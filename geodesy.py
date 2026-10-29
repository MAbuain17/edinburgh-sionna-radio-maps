"""WGS84 UTM zone 30N forward/inverse transforms (Snyder series).

Local study only; verified round-trip during the build. No native GIS runtime.
"""
import numpy as np
A=6378137.;E=0.0066943799901413165;EP=E/(1-E);K=.9996;L0=np.deg2rad(-3.)
def forward(lon,lat):
    p=np.deg2rad(lat);l=np.deg2rad(lon);s=np.sin(p);c=np.cos(p);t=np.tan(p)
    n=A/np.sqrt(1-E*s*s);T=t*t;C=EP*c*c;a=c*(l-L0)
    M=A*((1-E/4-3*E**2/64-5*E**3/256)*p-(3*E/8+3*E**2/32+45*E**3/1024)*np.sin(2*p)+(15*E**2/256+45*E**3/1024)*np.sin(4*p)-(35*E**3/3072)*np.sin(6*p))
    x=500000+K*n*(a+(1-T+C)*a**3/6+(5-18*T+T*T+72*C-58*EP)*a**5/120)
    y=K*(M+n*t*(a*a/2+(5-T+9*C+4*C*C)*a**4/24+(61-58*T+T*T+600*C-330*EP)*a**6/720))
    return x,y
def inverse(x,y):
    mu=np.asarray(y)/K/(A*(1-E/4-3*E**2/64-5*E**3/256));e1=(1-np.sqrt(1-E))/(1+np.sqrt(1-E))
    p=mu+(3*e1/2-27*e1**3/32)*np.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*np.sin(4*mu)+(151*e1**3/96)*np.sin(6*mu)+1097*e1**4/512*np.sin(8*mu)
    c=np.cos(p);t=np.tan(p);n=A/np.sqrt(1-E*np.sin(p)**2);r=A*(1-E)/(1-E*np.sin(p)**2)**1.5;T=t*t;C=EP*c*c;d=(np.asarray(x)-500000)/(n*K)
    lat=p-n*t/r*(d*d/2-(5+3*T+10*C-4*C*C-9*EP)*d**4/24+(61+90*T+298*C+45*T*T-252*EP-3*C*C)*d**6/720)
    lon=L0+(d-(1+2*T+C)*d**3/6+(5-2*C+28*T-3*C*C+8*EP+24*T*T)*d**5/120)/c
    return np.rad2deg(lon),np.rad2deg(lat)
