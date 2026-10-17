# Synthetic X11 clients for the isolated Gamescope focus regression.
# Does not launch Steam or access a user home.
import ctypes as C,time,json,os
x=C.CDLL('libX11.so.6'); P=C.c_void_p; U=C.c_ulong
x.XOpenDisplay.restype=P;x.XOpenDisplay.argtypes=[C.c_char_p]
d=x.XOpenDisplay(None);assert d,'no DISPLAY'
def setup(n,rest,args):
 f=getattr(x,n);f.restype=rest;f.argtypes=args;return f
root=setup('XDefaultRootWindow',U,[P])(d)
atom=setup('XInternAtom',U,[P,C.c_char_p,C.c_int])
change=setup('XChangeProperty',C.c_int,[P,U,U,U,C.c_int,C.c_int,P,C.c_int])
create=setup('XCreateSimpleWindow',U,[P,U,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_uint,U,U])
store=setup('XStoreName',C.c_int,[P,U,C.c_char_p]);mapw=setup('XMapWindow',C.c_int,[P,U]);flush=setup('XSync',C.c_int,[P,C.c_int])
get=setup('XGetWindowProperty',C.c_int,[P,U,U,C.c_long,C.c_long,C.c_int,U,C.POINTER(U),C.POINTER(C.c_int),C.POINTER(U),C.POINTER(U),C.POINTER(P)])
def prop(w,n,values):
 a=(U*len(values))(*values);change(d,w,atom(d,n.encode(),0),6,32,0,C.cast(a,P),len(values));flush(d,0)
def read(n):
 typ=U();fmt=C.c_int();count=U();left=U();data=P();get(d,root,atom(d,n.encode(),0),0,1024,0,0,C.byref(typ),C.byref(fmt),C.byref(count),C.byref(left),C.byref(data))
 return list(C.cast(data,C.POINTER(U))[:count.value]) if data.value and fmt.value==32 else []
wins={}
for label,appid,color in [('steam',769,0xeeeeee),('game',2968420,0x222222)]:
 w=create(d,root,0,0,640,480,0,0,color);wins[label]=w;store(d,w,label.encode());prop(w,'STEAM_GAME',[appid]);mapw(d,w);flush(d,0);time.sleep(.5)
result={'display':os.environ.get('DISPLAY'),'windows':wins,'initial':{},'requests':[]}
def snapshot():return {n:read(n) for n in ['GAMESCOPE_FOCUSABLE_APPS','GAMESCOPE_FOCUSED_WINDOW','GAMESCOPE_FOCUSED_APP','GAMESCOPE_FOCUSABLE_WINDOWS','GAMESCOPECTRL_BASELAYER_APPID']}
time.sleep(1);result['initial']=snapshot()
for appid in [2968420,769,2968420,769]:
 prop(root,'GAMESCOPECTRL_BASELAYER_APPID',[appid]);time.sleep(.7);result['requests'].append({'requested':appid,**snapshot()})
print('FOCUS_RESULT='+json.dumps(result),flush=True)
