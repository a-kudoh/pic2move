#! /usr/bin/python
# encoding: utf-8

import os,sys
import binascii
import struct
import zlib
import time

class container:
    def __init__(self, name=None):
        if name:
            self.name=name
    def __repr__(self):
        r=[]
        for i in dir(self):
            if i[:2]!="__" and i!="name":
                r.append("%s:%s" %(i, repr(getattr(self, i))))
        return ", ".join(r)
    def __str__(self):
        r=[]
        for i in dir(self):
            if i[:2]!="__" and i!="name":
                d=repr(getattr(self, i))
                if len(d)>20:
                    d=d[:20]+"..."
                r.append("%s:%s" %(i, d))
        return ", ".join(r)
    def __add__(self, c):
        if hasattr(c, "name"):
            if hasattr(self, c.name):
                if type(getattr(self, c.name))==type([]):
                    getattr(self, c.name).append(c)
                else:
                    setattr(self, c.name, [getattr(self, c.name), c])
            else:
                setattr(self, c.name, c)
        else:
            raise TypeError#, "unsupported operand +"
        return self

class png:
    SIGNATURE_LENGTH=8
    SIGNATURE=(137, 80, 78, 71, 13, 10, 26, 10)
    palette=None
    def __init__(self):
        self.decobj=zlib.decompressobj()
        self.idat=""
    def read(self, fp):
        r=container()
        for i in self.each_chunk_fp(fp):
            try:
                fn=getattr(self, "parse_%s" %(i[1]))
                z=fn(i)
                print (i[1]+":",z)
                r+=z
            except AttributeError, detail:
                #print detail
                print (i)
        return r
    def parse(self, data):
        r=container()
        self.data=data
        self.sig=self.parse_signature(data)
        if self.sig!=self.SIGNATURE:
            raise Exception, "invalid signature: %s" %(self.sig)
        for i in self.each_chunk():
            try:
                fn=getattr(self, "parse_%s" %(i[1]))
                z=fn(i)
                r+=z
            except AttributeError, detail:
                #print detail
                print (i)
        return r
    def parse_signature(self, data):
        "signature: (137 'P' 'N' 'G' '\r' '\n' 26 '\n')"
        return struct.unpack("%dB" %(self.SIGNATURE_LENGTH), data[:self.SIGNATURE_LENGTH])
    def parse_IHDR(self, d):
        r=container(d[1])
        length_should=struct.calcsize(">IIbbbbb")
        if length_should!=d[0]:
            raise Exception, "IHDR length mismatch: %d vs. %d" %(length_should, d[0])
        ihdr=struct.unpack(">IIbbbbb", d[2])
        r.width, r.height, r.depth, r.colortype, r.compress, \
                 r.filtering, r.interlace = ihdr
        r.dataraw=d[2]
        if r.compress!=0:
            raise Exception, "invalid compress value: %d" %(r.compress)
        if r.filtering!=0:
            raise Exception, "invalid filter value: %d" %(r.filtering)
        return r
    def parse_IDAT(self, d):
        r=container(d[1])
        r.data=self.decobj.decompress(d[2])
        r.dataraw=d[2]
        return r
    def parse_PLTE(self, d):
        r=container(d[1])
        if d[0]%3!=0:
            raise Exception, "invalid PLTE length: %d (/3=%d)" %(d[0], d[0]%3)
        r.palette=struct.unpack("%dB" %(d[0]), d[2])
        return r
    def parse_IEND(self, d):
        r=container(d[1])
        return r
    # optional
    def parse_sBIT(self, d):
        r=container(d[1])
        r.sbit=struct.unpack(">%dB" %(d[0]), d[2])
        return r
    def parse_tEXt(self, d):
        r=container(d[1])
        r.kw,r.txt=d[2].split("\0")
        return r
    def parse_zTXt(self, d):
        r=container(d[1])
        r.kw,rest=d[2].split("\0", 1)
        r.compress=struct.unpack(">B", rest[0])
        if r.compress!=0:
            raise Exception, "invalid compress: %d" %(r.compress)
        r.txt=zlib.decompress(rest[1:])
        return r
    def parse_iTXt(self, d):
        r=container(d[1])
        r.kw,rest=d[2].split("\0", 1)
        r.compress,r.cmthod=struct.unpack(">BB", rest[0:1])
        r.lang,r.kwlocal,r.txt=rest[2:].split("\0")
        if r.compress==1:
            if r.cmthod!=0:
                raise Exception, "invalid compress: %d" %(r.cmthod)
            r.txt=zlib.decompress(r.txt)
        if r.lang:
            r.txt=unicode(r.txt, lang)
        return r
    def parse_tRNS(self, d):
        r=container(d[1])
        if d[0]==2:
            r.gley,=struct.unpack(">H", d[2])
        if d[0]==6:
            r.rgb=struct.unpack(">3H", d[2])
        if d[0]%3==0:
            r.indexed=struct.unpack(">%dB" %(d[0]), d[2])
        return r
    def parse_gAMA(self, d):
        r=container(d[1])
        r.gamma,=struct.unpack(">I", d[2])
        return r
    def parse_pHYs(self, d):
        r=container(d[1])
        r.x, r.y, r.unit=struct.unpack(">IIB", d[2])
        if r.unit==1:
            r.unit="meter"
        else:
            r.unit="unknown"
        return r
    # apng extension
    def parse_acTL(self, d):
        r=container(d[1])
        if d[0]!=8:
            raise Exception, "invalid acTL length: %d vs. 8" %(d[0])
        r.frames, r.plays=struct.unpack(">II", d[2])
        return r
    def parse_fcTL(self, d):
        self.decobj=zlib.decompressobj()
        if d[0]!=26:
            raise Exception, "invalid fcTL length: %d vs. 26" %(d[0])
        r=container(d[1])
        r.seqno, r.width, r.height, r.xoff, r.yoff, \
                 r.delay_num, r.delay_den, \
                 r.dispose, r.blend = struct.unpack(">5I2H2B", d[2])
        return r
    def parse_fdAT(self, d):
        r=container(d[1])
        r.seqno,=struct.unpack(">I", d[2][:4])
        r.data=self.decobj.decompress(d[2][4:])
        r.dataraw=d[2][4:]
        return r
    def each_chunk(self):
        st=self.SIGNATURE_LENGTH
        while st<len(self.data):
            # parse chunkhdr
            length, chunktype=struct.unpack(">I4s", self.data[st:st+8])
            chunkdata = self.data[st+8:st+8+length]
            crc,=struct.unpack(">i", self.data[st+8+length:st+8+length+4])
            # check crc
            crc2=binascii.crc32(self.data[st+4:st+8+length])
            if crc!=crc2:
                raise Exception, "crc mismatch: %x vs. %x" %(crc, crc2)
            st+=8+length+4
            yield length, chunktype, chunkdata, crc
            if chunktype=="IEND":
                if len(self.data)-st:
                    print "rest data: %d" %(len(self.data)-st)
                break
    def each_chunk_fp(self, fp):
        sign=fp.read(self.SIGNATURE_LENGTH)
        self.sig=self.parse_signature(sign)
        if self.sig!=self.SIGNATURE:
            raise Exception, "invalid signature: %s" %(self.sig)
        while True:
            length, chunktype = struct.unpack(">I4s", fp.read(8))
            chunkdata = fp.read(length)
            crc, = struct.unpack(">i", fp.read(4))
            # check CRC
            crc2 = binascii.crc32(chunktype)
            crc2 = binascii.crc32(chunkdata, crc2)
            assert crc2 == crc
            yield length, chunktype, chunkdata, crc
            if chunktype=="IEND":
                break

    def store_signature(self, fp):
        pkt=""
        for i in self.SIGNATURE:
            pkt+=struct.pack("B", i)
        fp.write(pkt)
    def store_pkt(self, fp, chunktype, data):
        pkt=struct.pack(">I4s", len(data), chunktype)
        crc=binascii.crc32(pkt[4:])
        crc=binascii.crc32(data, crc)
        pkt+=data
        pkt+=struct.pack(">i", crc)
        fp.write(pkt)
    def store_IEND(self, fp):
        self.store_pkt(fp, "IEND", "")
    def store_IHDR(self, fp, width, height, depth, colortype, compress=0, filtering=0, interlace=0):
        pkt=struct.pack(">IIbbbbb", width, height, depth, colortype, compress, filtering, interlace)
        self.store_pkt(fp, "IHDR", pkt)
    def store_IDAT(self, fp, data, rawp=True):
        if rawp:
            data=zlib.compress(data)
        self.store_pkt(fp, "IDAT", data)
    def store_PLTE(self, fp, palette):
        pkt=""
        for i in palette:
            pkt+=struct.pack(">3B", i)
        self.store_pkt(fp, "PLTE", pkt)
    # optional
    def store_tEXt(self, fp, keyword, value):
        pkt="\0".join((keyword, value))
        self.store_pkt(fp, "tEXt", pkt)
    def store_zTXt(self, fp, keyword, value):
        pkt="\0\0".join((keyword, zlib.compress(value)))
        self.store_pkt(fp, "zTXt", pkt)
    def store_iTXt(self, fp, keyword, value, lang, kwlocal, compress=True):
        pkt=keyword
        pkt+="\0"
        if compress:
            value=zlib.compress(value)
            pkt+="\1\0"
        else:
            pkt+="\0\0"
        pkt+="\0".join((lang, kwlocal, value))
        self.store_pkt(fp, "iTXt", pkt)
    def store_pHYs(self, fp, x, y, unit=1):
        # unit: 1=meter, other=undefined
        pkt=struct.pack(">IIB", x, y, unit)
        self.store_pkt(fp, "pHYs", pkt)
    def store_gAMA(self, fp, gamma):
        pkt=struct.pack(">I", gamma)
        self.store_pkt(fp, "gAMA", pkt)
    def store_tRNS(self, fp, trns, colortype):
        if colortype==0:
            assert type(trns)==type(1)
            pkt=struct.pack(">H", trns)
        elif colortype==2:
            assert len(trns)==3
            pkt=struct.pack(">3H", trns)
        elif colortype==3:
            pkt=struct.pack(">%dB" %(len(trns)), trns)
        self.store_pkt(fp, "tRNS", pkt)
    # apng extension
    def store_acTL(self, fp, frames, plays=0):
        pkt=struct.pack(">II", frames, plays)
        self.store_pkt(fp, "acTL", pkt)
    def store_fcTL(self, fp, frameid, size, offset, delay_ms, dispose=0, blend=0):
        pkt=struct.pack(">5I2H2B", frameid, size[0], size[1], offset[0], offset[1], delay_ms, 1000, dispose, blend)
        self.store_pkt(fp, "fcTL", pkt)
    def store_fdAT(self, fp, frameid, data, rawp=True):
        pkt=struct.pack(">I", frameid)
        if rawp:
            data=zlib.compress(data)
        pkt+=data
        self.store_pkt(fp, "fdAT", pkt)

def apng2pngs(apngfile, basen):
    a=png()
    n=1
    basepkts=[]
    o=None
    for i in a.each_chunk_fp(apngfile):
        if i[1]=="fcTL":
            if o:
                a.store_IEND(o)
            o=file("%s-%d.png" %(basen, n), "w")
            n+=1
            a.store_signature(o)
            for j in basepkts:
                a.store_pkt(o, j[0], j[1])
        elif i[1]=="acTL":
            pass
        elif i[1]=="fdAT":
            a.store_pkt(o, "IDAT", i[2][4:])
        elif i[1]=="IDAT":
            if o:
                a.store_pkt(o, "IDAT", i[2])
        else:
            basepkts.append((i[1], i[2]))
    if o:
        a.store_IEND(o)

def apngview(fname):
    from PIL import Image, ImageTk
    from Tkinter import Label,PhotoImage,Frame
    import StringIO
    class App(Frame):
        def quit(self, ev): self.master.destroy()
        def next(self, n):
            cur=self.actl.fcTL[n]
            nex=None
            if n+1<len(self.actl.fcTL):
                nexi=n+1
                nex=self.actl.fcTL[nexi]
            elif self.actl.plays!=1:
                nexi=self.actl.start
                nex=self.actl.fcTL[nexi]
            self.image1=ImageTk.PhotoImage(cur.im)
            self.la.config(image=self.image1,
                           width=self.image1.width(),
                           height=self.image1.height())
            if nex:
                delay=int((float(nex.delay_num)/nex.delay_den)*100)
                #print "delay", delay
                self.after(delay, self.next, nexi)
        def start(self, ev):
            self.next(self.actl.start)

        def open(self, event):
            filename = tkFileDialog.askopenfilename()
            if filename != "":
                im = PIL.Image.open(filename)
            if im.mode == "1": # bitmap image
                self.image1 = PIL.ImageTk.BitmapImage(im, foreground="white")
            else:              # photo image
                self.image1 = PIL.ImageTk.PhotoImage(im)
            self.la.config(image=self.image1,
                           width=self.image1.width(), height=self.image1.height())
        def init(self):
            self.image1 = PhotoImage()
            la = self.la = Label(self, image=self.image1, bg="#000000",
                                 width=100, height=100)
            # la.bind("<Button-1>", self.open)
            la.bind("<Button-3>", self.quit)
            la.bind("<Button-1>", self.start)
            la.pack()
        def __init__(self, master=None):
            Frame.__init__(self, master)
            self.master.title('APNGビューア')
            self.init()
            self.pack()
        def load(self, fname):
            f=file(fname)
            p=png()
            p.get_str=False
            size=(None,None)
            self.actl,fctl,fdat=None,None,None
            ihdr,plte=None,None
            for d in p.each_chunk_fp(f):
                ln,ct,dt,crc = d
                if ct=="IHDR":
                    ihdr=p.parse_IHDR(d)
                    if ihdr.colortype==0: mode="L"
                    elif ihdr.colortype==2: mode="RGB"
                    elif ihdr.colortype==3: mode="P"
                    elif ihdr.colortype==4: mode="L"
                    elif ihdr.colortype==6: mode="RGBA"
                    bits=ihdr.depth
                    self.la.config(width=ihdr.width, height=ihdr.height)
                    print ihdr
                elif ct=="PLTE":
                    plte=p.parse_PLTE(d)
                    print plte
                elif ct=="acTL":
                    self.actl=p.parse_acTL(d)
                elif ct=="fcTL":
                    fctl=p.parse_fcTL(d)
                    self.actl+=fctl
                    size=(fctl.width, fctl.height)
                elif ct=="fdAT":
                    fdat=p.parse_fdAT(d)
                    fctl+=fdat
            if self.actl.frames==1:
                self.actl.fcTL=[self.actl.fcTL]
            if len(self.actl.fcTL)!=self.actl.frames:
                raise Exception, "frame count mismatch: %d vs. %d" %(len(actl.fcTL), actl.frames)
            for i in self.actl.fcTL:
                if not hasattr(i, "fdAT"):
                    # print i
                    continue
                elif not hasattr(self.actl, "start"):
                    self.actl.start=i.seqno
                if type(i.fdAT)==type([]):
                    data="".join(map(lambda f: f.dataraw, i.fdAT))
                    # print "len(dataN) =", len(data)
                else:
                    data=i.fdAT.dataraw
                    # print "len(data) =", len(data)
                sio=StringIO.StringIO()
                p.store_signature(sio)
                p.store_pkt(sio, "IHDR", ihdr.dataraw)
                p.store_pkt(sio, "IDAT", data)
                p.store_pkt(sio, "IEND", "")
                sio.seek(0)
                i.im=Image.open(sio)
                # im=Image.fromstring(mode, (i.width, i.height), data, "raw")
                if plte:
                    i.im.putpalette(plte.palette)

    app=App()
    app.load(fname)
    app.mainloop()

# dump
def main0():
    for i in sys.argv[1:]:
        print (i)
        a=png()
        print (a.read(file(i)))

# convert apng2pngs
def main1():
    base="pngfile"
    if len(sys.argv)>=3 and sys.argv[2]!="":
        base=sys.argv[2]
    if len(sys.argv)==1:
        print ("Usage: %s apngfile [output-base]" %(sys.argv[0]))
        sys.exit(0)
    apng2pngs(file(sys.argv[1]), base)

# view
def main2():
    for i in sys.argv[1:]:
        apngview(i)

main2()
