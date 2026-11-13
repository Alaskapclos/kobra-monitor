/* SPDX-License-Identifier: GPL-3.0-only */
/* Compile as Objective-C. Keep the signed GUI host alive while its worker runs,
 * so macOS can attribute helper network access to this application. */
#import <Cocoa/Cocoa.h>
#include <mach-o/dyld.h>
#include <limits.h>
#include <unistd.h>

@interface KobraHost : NSObject <NSApplicationDelegate>
@property NSString *python;
@property NSArray<NSString *> *arguments;
@property NSTask *primary;
@property BOOL terminating;
@property int result;
@end

@implementation KobraHost
- (void)startTask:(BOOL)primary {
    NSTask *task=[NSTask new];
    task.executableURL=[NSURL fileURLWithPath:self.python];
    task.arguments=self.arguments;
    __weak KobraHost *owner=self;
    task.terminationHandler=^(NSTask *finished) {
        if (!primary) return;
        dispatch_async(dispatch_get_main_queue(), ^{
            KobraHost *host=owner;
            host.result=finished.terminationStatus;
            if (host.terminating) [NSApp replyToApplicationShouldTerminate:YES];
            else [NSApp terminate:nil];
        });
    };
    if (primary) self.primary=task;
    NSError *error=nil;
    if (![task launchAndReturnError:&error]) {
        NSAlert *alert=[NSAlert new];
        alert.messageText=@"Kobra Monitor konnte nicht gestartet werden.";
        alert.informativeText=@"Bitte das Testpaket erneut entpacken. Deine lokalen Daten bleiben erhalten.";
        [alert runModal];
        if (primary) [NSApp terminate:nil];
    }
}
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [self startTask:YES];
}
- (BOOL)applicationShouldHandleReopen:(NSApplication *)sender hasVisibleWindows:(BOOL)visible {
    if (self.primary.running && !self.terminating) [self startTask:NO];
    return YES;
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    if (!self.primary.running) return NSTerminateNow;
    if (self.terminating) return NSTerminateLater;
    self.terminating=YES;
    NSTask *stop=[NSTask new];
    stop.executableURL=[NSURL fileURLWithPath:self.python];
    NSMutableArray *args=[self.arguments mutableCopy];
    [args addObjectsFromArray:@[@"--mode",@"stop"]];
    stop.arguments=args;
    NSError *error=nil;
    if (![stop launchAndReturnError:&error]) {self.terminating=NO;return NSTerminateCancel;}
    return NSTerminateLater;
}
@end

int main(int argc, char **argv) {
    @autoreleasepool {
        char path[PATH_MAX],resolved[PATH_MAX];uint32_t size=sizeof(path);
        if (_NSGetExecutablePath(path,&size)!=0 || !realpath(path,resolved)) return 1;
        NSString *app=[[[[NSString stringWithUTF8String:resolved] stringByDeletingLastPathComponent]
                      stringByDeletingLastPathComponent] stringByDeletingLastPathComponent];
        NSString *root=[app stringByAppendingPathComponent:@"Contents/Resources/payload"];
        KobraHost *host=[KobraHost new];
        host.python=[root stringByAppendingPathComponent:@"runtime/monitor/bin/python3.14"];
        NSMutableArray *args=[NSMutableArray arrayWithArray:@[@"-I",@"-B",@"-X",@"utf8",
            [root stringByAppendingPathComponent:@"app/monitor/macos_entry.py"],@"--bundle",root,@"--foreground"]];
        for (int i=1;i<argc;i++) [args addObject:[NSString stringWithUTF8String:argv[i]]];
        host.arguments=args;
        [NSApplication sharedApplication];
        NSApp.delegate=host;
        [NSApp run];
        return host.result;
    }
    return 0;
}
