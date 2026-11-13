from pathlib import Path
import ast,errno,os,sys,tempfile,types,unittest
from unittest.mock import patch
FIXED=(Path(__file__).resolve().parents[1]/'suite/desktop.py').read_text()
ORIGINAL=FIXED.replace("        # Windows also denies reads through another handle to a locked byte.\n        # Inspect the file length without reading the byte owned by that process.\n        try:\n            if os.fstat(self.stream.fileno()).st_size == 0:\n                self.stream.write(b'0'); self.stream.flush()\n            self.stream.seek(0)\n        except BaseException:\n            self.stream.close(); self.stream = None\n            raise\n","        self.stream.seek(0)\n        if not self.stream.read(1):\n            self.stream.write(b'0'); self.stream.flush()\n        self.stream.seek(0)\n")
def lock_class(text,backend):
 tree=ast.parse(text);node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='InstallationLock')
 scope={'Path':Path,'os':backend};exec(compile(ast.Module(body=[node],type_ignores=[]),'lock-fixture','exec'),scope);return scope['InstallationLock']

class InstallationLockWindowsTests(unittest.TestCase):
 def fixture(self,busy):
  self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
  path=Path(self.temporary.name)/'desktop.lock';path.write_bytes(b'0')
  state={'busy':busy,'read_calls':0,'unlocks':0};streams=[]
  class Stream:
   def __init__(self):self.real=open(path,'a+b');streams.append(self)
   def read(self,n):
    state['read_calls']+=1
    if state['busy']:raise PermissionError(errno.EACCES,'Permission denied')
    return self.real.read(n)
   def __getattr__(self,n):return getattr(self.real,n)
  def locking(fd,mode,size):
   self.assertEqual(size,1)
   if mode==1:
    if state['busy']:raise PermissionError(errno.EACCES,'Permission denied')
    state['busy']=True
   else:state.update(busy=False,unlocks=state['unlocks']+1)
  module=types.SimpleNamespace(locking=locking,LK_NBLCK=1,LK_UNLCK=2)
  backend=types.SimpleNamespace(name='nt',fstat=os.fstat)
  return path,state,streams,Stream,module,backend
 def test_old_windows_busy_lock_read_reproduces_permission_denied(self):
  p,state,streams,stream,module,backend=self.fixture(True);klass=lock_class(ORIGINAL,backend)
  with patch.object(Path,'open',side_effect=lambda *a,**k:stream()),patch.dict(sys.modules,{'msvcrt':module}):
   with self.assertRaises(PermissionError):klass(p).acquire()
  for s in streams:s.close()
  self.assertEqual(state['read_calls'],1)
 def test_corrected_windows_busy_lock_returns_false_and_closes_handle(self):
  p,state,streams,stream,module,backend=self.fixture(True);klass=lock_class(FIXED,backend)
  with patch.object(Path,'open',side_effect=lambda *a,**k:stream()),patch.dict(sys.modules,{'msvcrt':module}):
   lock=klass(p);self.assertFalse(lock.acquire());self.assertIsNone(lock.stream)
  self.assertEqual(state['read_calls'],0);self.assertTrue(all(s.closed for s in streams))
 def test_corrected_windows_empty_file_release_and_reacquire(self):
  p,state,streams,stream,module,backend=self.fixture(False);p.write_bytes(b'');klass=lock_class(FIXED,backend)
  with patch.object(Path,'open',side_effect=lambda *a,**k:stream()),patch.dict(sys.modules,{'msvcrt':module}):
   a=klass(p);b=klass(p);self.assertTrue(a.acquire());self.assertFalse(b.acquire());a.close();self.assertTrue(b.acquire());b.close()
  self.assertEqual(state['read_calls'],0);self.assertEqual(p.read_bytes(),b'0');self.assertEqual(state['unlocks'],2)
 def test_real_open_access_error_is_not_claimed_as_running_app(self):
  p,state,streams,stream,module,backend=self.fixture(False);klass=lock_class(FIXED,backend)
  with patch.object(Path,'open',side_effect=PermissionError(errno.EACCES,'Access denied')),patch.dict(sys.modules,{'msvcrt':module}):
   with self.assertRaises(PermissionError):klass(p).acquire()
 def test_real_posix_exclusion_and_reacquire(self):
  with tempfile.TemporaryDirectory() as folder:
   klass=lock_class(FIXED,os);a=klass(Path(folder)/'desktop.lock');b=klass(a.path)
   self.assertTrue(a.acquire());self.assertFalse(b.acquire());a.close();self.assertTrue(b.acquire());b.close()

if __name__=='__main__':unittest.main(verbosity=2)
