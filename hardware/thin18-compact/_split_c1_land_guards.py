"""Primary land and net guards for the 2026-10-02 connector/ESD ECOs."""
import re
from _split_c1_sourcing import blocks,property_value

def verify_20261002_lands(core,display):
    def check(text,ref,mpn,pose,expected):
        f=next(b for _,_,b in blocks(text,r'\(footprint\s') if property_value(b,'Reference')==ref)
        actual=tuple(float(v or 0) for v in re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)',f).groups())
        if property_value(f,'MPN')!=mpn or actual!=pose or '(model ' in f:raise ValueError(ref+' identity/pose/model differs')
        pads=[]
        for _,_,p in blocks(f,r'\(pad\s'):
            n=re.match(r'\(pad\s+"([^"]+)"',p).group(1)
            xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
            sz=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
            net=re.search(r'\(net\s+"([^"]+)"',p)
            pads.append((n,xy,sz,net.group(1) if net else None))
        if sorted(pads)!=sorted(expected):raise ValueError(ref+' reviewed primary lands/pin mapping differ')
    esd=[]
    io={1:'USB_DP',2:'USB_DM',3:'GND',4:'USB_CC1',5:'USB_CC2',8:'GND'}
    for n in range(1,11):
        y=-1+(n-1)*.5 if n<=5 else 1-(n-6)*.5
        xy=(-.3875 if n<=5 else .3875,y);sz=(.625,.25)
        if n==3:xy=(-.35,0);sz=(.7,.45)
        elif n==8:xy=(.4125,0);sz=(.575,.45)
        esd.append((str(n),xy,sz,io.get(n,'unconnected-(D201-NC-Pad'+str(n)+')')))
    check(core,'D201','LRC8804FDT1G',(39,57.5,90),esd)
    check(core,'J301','HC-HY-2AWT',(62,12,90),[
        ('1',(-1,-2.21),(1.2,3.8),'BAT_CONN_P'),('2',(1,-2.21),(1.2,3.8),'GND'),
        ('MP',(-3.2,5.39),(1.2,3.7),None),('MP',(3.2,5.39),(1.2,3.7),None)])
    names=[None,'GDR','RESE',None,'VSH2','GND','GND','GND','BUSY','RESET','DC','CS','SCLK','MOSI','EPD_3V3','EPD_3V3','GND','VDD1V5',None,'VSH1','VGH','VSL','VGL','VCOM']
    fpc=[(str(n),(-5.75+(n-1)*.5,-1.85),(.3,.65),
          '/'+name if name else 'unconnected-(J2-Pin_'+str(n)+'-Pad'+str(n)+')')
         for n,name in enumerate(names,1)]
    fpc += [('MP',(-6.635,.005),(.3,.76),None),('MP',(6.635,.005),(.3,.76),None)]
    check(display,'J2','X05A10L24G',(23,29,0),fpc)
