# 由 tools/sketch_src/灵感/ 的原始截图生成速写灵感气泡的多尺寸掩码模板（只留图标，背景涂成纯绿 0,255,0 供 green_mask 忽略）
# 用法：python3 tools/gen_sketch_templates.py
import cv2,numpy as np,glob,os,sys
from scipy import ndimage
SRC='tools/sketch_src/灵感/'
OUT=sys.argv[1] if len(sys.argv)>1 else 'assets/resource/image/sketch/灵感'; os.makedirs(OUT,exist_ok=True)
scales=[0.6,0.67,0.75,0.85,0.92,1.0,1.08,1.16,1.25,1.4,1.5,1.6]
def icon_mask(img):
    b,g,r=[img[...,i].astype(int) for i in range(3)]
    m=(r>110)&(r-b>45)&(g>50)
    m=ndimage.binary_closing(m,iterations=2); m=ndimage.binary_fill_holes(m)
    lab,n=ndimage.label(m)
    if n>1:
        sizes=ndimage.sum(m,lab,range(1,n+1)); m=lab==(np.argmax(sizes)+1)
    return ndimage.binary_dilation(m,iterations=1)
res={}
for f in sorted(glob.glob(SRC+'*.png')):
    name=os.path.basename(f)[:-4]
    img=cv2.imdecode(np.fromfile(f,np.uint8),cv2.IMREAD_COLOR)
    m=icon_mask(img)
    ys,xs=np.where(m); img=img[ys.min():ys.max()+1,xs.min():xs.max()+1]; m=m[ys.min():ys.max()+1,xs.min():xs.max()+1]
    for s in scales:
        w=max(8,round(img.shape[1]*s)); h=max(8,round(img.shape[0]*s))
        im=cv2.resize(img,(w,h),interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
        mm=cv2.resize(m.astype(np.uint8),(w,h),interpolation=cv2.INTER_NEAREST).astype(bool)
        im[~mm]=(0,255,0)
        p=f'{OUT}/{name}_{int(s*100)}.png'
        cv2.imencode('.png',im)[1].tofile(p)
