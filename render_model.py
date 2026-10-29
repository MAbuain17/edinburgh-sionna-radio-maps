"""Render the delivered geometry with Mitsuba's scalar CPU renderer."""
from pathlib import Path
import os,xml.etree.ElementTree as ET
import mitsuba as mi
mi.set_variant('scalar_rgb')
R=Path(__file__).resolve().parent
os.chdir(R/'scene')
tree=ET.parse('scene.xml');root=tree.getroot()
ET.SubElement(root,'integrator',type='path')
light=ET.SubElement(root,'emitter',type='constant');ET.SubElement(light,'rgb',name='radiance',value='0.9 0.9 0.9')
scene=mi.load_string(ET.tostring(root,encoding='unicode'))
sensor=mi.load_dict({'type':'perspective','fov':42,'to_world':mi.ScalarTransform4f().look_at(origin=[950,-1120,1000],target=[20,65,0],up=[0,0,1]),'film':{'type':'hdrfilm','width':1400,'height':1000,'rfilter':{'type':'tent'}},'sampler':{'type':'independent','sample_count':32}})
img=mi.render(scene,sensor=sensor,spp=32)
mi.util.write_bitmap(str(R/'figures/campus_3d.png'),img)
print(R/'figures/campus_3d.png')
import sys
if sys.platform=='win32':
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
