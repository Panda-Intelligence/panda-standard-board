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
            n=re.match(r'\(pad\s+"([^"]*)"',p).group(1)
            xy=tuple(map(float,re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
            sz=tuple(map(float,re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)',p).groups()))
            net=re.search(r'\(net\s+"([^"]*)"',p)
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

    sdnet={1:'SDMMC_D2_CARD',2:'SDMMC_D3_CARD',3:'SDMMC_CMD_CARD',4:'3V3_SD',5:'SDMMC_CLK_CARD',6:'GND',7:'SDMMC_D0_CARD',8:'SDMMC_D1_CARD'}
    sd=[(str(n),(round(2.27-(n-1)*1.1,6),-.8),(.6,1.6),sdnet[n]) for n in range(1,9)]
    sd += [('9',(-6.53,-.8),(.6,1.6),'SD_CD'),('10',(-7.73,.5),(1.2,1.8),'GND'),
           ('SH',(7.77,9.8),(1.2,2.2),'GND'),('SH',(-7.73,9.8),(1.2,2.2),'GND'),('SH',(6.87,.25),(1.6,1.5),'GND'),
           ('',(-4.93,10.2),(1,1),None),('',(3.07,10.2),(1,1),None)]
    check(core,'J501','TF-122-CCP9',(81.75,17.315,90),sd)
    f=next(b for _,_,b in blocks(core,r'\(footprint\s') if property_value(b,'Reference')=='J501')
    holes=[p for _,_,p in blocks(f,r'\(pad\s') if p.startswith('(pad ""')]
    if len(holes)!=2 or any('np_thru_hole circle' not in p or '(drill 1)' not in p for p in holes):
        raise ValueError('J501 primary locating holes differ')
    l=next(b for _,_,b in blocks(core,r'\(footprint\s') if property_value(b,'Reference')=='L402')
    if property_value(l,'MPN')!='MWSA0402S-1R0MT' or property_value(l,'LCSC')!='C408332':
        raise ValueError('L402 reviewed MT variant/code differs')
