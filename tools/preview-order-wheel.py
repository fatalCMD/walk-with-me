"""Render the actual wheel draw code through ImGui, then rasterize its triangles.

Requires the optional ImGui test source, Pillow/numpy, and Node's sharp for SVGs.
No game process is opened. Generated C++ is derived from menu_ui.cpp/order_visuals.cpp.
"""
from pathlib import Path
import argparse, json, subprocess, struct
import numpy as np
from PIL import Image

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cmake',required=True)
p.add_argument('--node',required=True)
p.add_argument('--sharp',required=True)
args=p.parse_args()
root=Path(__file__).resolve().parents[1]
out=root/'build/wheel-visual-proof';out.mkdir(parents=True,exist_ok=True)
menu=(root/'src/menu_ui.cpp').read_text()
draw=menu.split('                auto text=[&](const char* value,V at,float size,Im::ImU32 color,float width){',1)[1]
draw='auto text=[&](const char* value,V at,float size,Im::ImU32 color,float width){'+draw.split('                if(padConfirm.exchange(false)',1)[0]
visuals=(root/'src/order_visuals.cpp').read_text().replace('#include "order_visuals.h"','')
cpp=r'''
#include "imgui.h"
#include "order_wheel.h"
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
namespace ImGuiMCP {
using namespace ImGui;using ::ImDrawList;using ::ImVec2;using ::ImU32;using ::ImTextureID;
namespace ImDrawListManager {
void AddText(ImDrawList*d,ImFont*f,float s,ImVec2 p,ImU32 c,const char*t){d->AddText(f,s,p,c,t);}
void AddCircle(ImDrawList*d,ImVec2 p,float r,ImU32 c,int n,float t){d->AddCircle(p,r,c,n,t);}
void AddCircleFilled(ImDrawList*d,ImVec2 p,float r,ImU32 c,int n){d->AddCircleFilled(p,r,c,n);}
void PathArcTo(ImDrawList*d,ImVec2 p,float r,float a,float b,int n){d->PathArcTo(p,r,a,b,n);}
void PathStroke(ImDrawList*d,ImU32 c,int f,float t){d->PathStroke(c,f,t);}
void AddImageQuad(ImDrawList*d,ImTextureID t,ImVec2 a,ImVec2 b,ImVec2 c,ImVec2 e,ImVec2 u,ImVec2 v,ImVec2 w,ImVec2 x,ImU32 col){d->AddImageQuad(t,a,b,c,e,u,v,w,x,col);}
}
}
std::vector<std::string> textures{"font"};
namespace SKSEMenuFramework {
ImTextureID LoadTexture(std::string path,ImVec2){textures.push_back(path);return (ImTextureID)(intptr_t)(textures.size()-1);}
}
namespace Wayfarer::OrderVisuals {
void Icon(ImDrawList*,ImVec2,float,int,float,float=1,bool=false);
}
'''+visuals+r'''
ImFont* inscription{};
struct Inscription {Inscription(){ImGui::PushFont(inscription);}~Inscription(){ImGui::PopFont();}};
int main(int argc,char**argv){
 using namespace Wayfarer;namespace Im=ImGuiMCP;namespace Draw=Im::ImDrawListManager;using V=Im::ImVec2;
 ImGui::CreateContext();auto& io=ImGui::GetIO();io.DisplaySize={1000,850};io.DeltaTime=1.0F/60;io.IniFilename=nullptr;
 io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeui.ttf",24);
 inscription=io.Fonts->AddFontFromFileTTF("package/SKSE/Plugins/Fonts/WalkWithMeInscription.ttf",28);
 unsigned char* pixels;int fw,fh;io.Fonts->GetTexDataAsRGBA32(&pixels,&fw,&fh);
 std::ofstream font("build/wheel-visual-proof/font.bin",std::ios::binary);font.write((char*)&fw,4);font.write((char*)&fh,4);font.write((char*)pixels,fw*fh*4);font.close();
 io.Fonts->SetTexID((ImTextureID)0);
 const int focus=argc>1?std::stoi(argv[1]):2;
 const float time=argc>2?std::stof(argv[2]):1.5F;
 Wheel::Motion motion;motion.Open(0);
 for(float t=0;t<time;t+=1.0F/60)motion.Update(1.0F/60,t<.55F?0:focus);
 float elapsed=time,centerElapsed=std::max(0.0F,time-.55F);
 const float fade=motion.visibility,w=650,radius=w*.40F*motion.Scale();
 const V origin{175,50},center{origin.x+w*.5F,origin.y+w*.48F};
 struct {bool enabled=true;int mode=0;} view;
 const char* profileNames[]{"Natural","Lead","Companion","Rear","Relax","Vanilla"};
 const auto gold=IM_COL32(197,180,136,255),muted=IM_COL32(149,146,137,255);
 ImGui::NewFrame();auto* draw=ImGui::GetBackgroundDrawList();
 '''+draw+r'''
 text("ACTIVE ORDER  /  Natural",{center.x,origin.y+w*.92F},w*.019F,gold,w*.8F);
 text("Click / 1-6: choose    Enter: confirm    Esc: back",{center.x,origin.y+w*.957F},w*.018F,muted,w*.95F);
 ImGui::Render();auto* data=ImGui::GetDrawData();
 std::ofstream file("build/wheel-visual-proof/triangles.bin",std::ios::binary);
 for(int list=0;list<data->CmdListsCount;++list){auto* d=data->CmdLists[list];
  for(const auto& cmd:d->CmdBuffer){if(cmd.UserCallback)continue;uint32_t texture=(uint32_t)(intptr_t)cmd.TextureId;
   for(unsigned i=0;i<cmd.ElemCount;i+=3){file.write((char*)&texture,4);
    for(unsigned k=0;k<3;++k){const auto& v=d->VtxBuffer[d->IdxBuffer[cmd.IdxOffset+i+k]+cmd.VtxOffset];file.write((char*)&v,sizeof(v));}
   }
  }
 }
 std::ofstream manifest("build/wheel-visual-proof/textures.txt");for(auto& t:textures)manifest<<t<<'\n';
 ImGui::DestroyContext();
}
'''
(out/'preview.cpp').write_text(cpp)
imgui=(root/'build/menu-audit/imgui').as_posix()
(out/'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.24)
project(WheelVisualProof LANGUAGES CXX)
add_executable(WheelVisualProof preview.cpp "{imgui}/imgui.cpp" "{imgui}/imgui_draw.cpp" "{imgui}/imgui_widgets.cpp" "{imgui}/imgui_tables.cpp")
target_include_directories(WheelVisualProof PRIVATE "{imgui}" "{root.as_posix()}/include")
target_compile_features(WheelVisualProof PRIVATE cxx_std_20)
''')
subprocess.run([args.cmake,'-S',str(out),'-B',str(out/'bin'),'-G','Visual Studio 17 2022','-A','x64'],check=True)
subprocess.run([args.cmake,'--build',str(out/'bin'),'--config','Release','--parallel','8'],check=True)
exe=out/'bin/Release/WheelVisualProof.exe'
subprocess.run([str(exe),'2','1.5'],cwd=root,check=True)
font=(out/'font.bin').read_bytes();fw,fh=struct.unpack_from('<ii',font)
atlas=np.frombuffer(font[8:],dtype=np.uint8).reshape(fh,fw,4)
textures=[atlas]
svg_paths=[]
for name in (out/'textures.txt').read_text().splitlines()[1:]:
    svg_paths.append(str(root/'package'/name.removeprefix('Data/')))
(out/'raster-assets.cjs').write_text('const sharp=require('+json.dumps(args.sharp)+');\nPromise.all('+json.dumps(svg_paths)+'.map((p,i)=>sharp(p,{density:288}).resize(768,768).png().toFile(__dirname+"/texture-"+i+".png"))).catch(e=>{console.error(e);process.exit(1)});')
subprocess.run([args.node,str(out/'raster-assets.cjs')],check=True)
textures += [np.asarray(Image.open(out/f'texture-{i}.png').convert('RGBA')) for i in range(len(svg_paths))]

def render(name):
    raw=(out/'triangles.bin').read_bytes()
    dtype=np.dtype([('x','<f4'),('y','<f4'),('u','<f4'),('v','<f4'),('col','<u4')])
    canvas=np.zeros((850,1000,3),dtype=np.float32)
    yy,xx=np.mgrid[:850,:1000];glow=np.maximum(0,1-np.hypot((xx-500)/650,(yy-370)/650))
    for c,base in enumerate((13,20,25)):canvas[:,:,c]=base+glow*(8+c*2)
    for at in range(0,len(raw),64):
        texture=struct.unpack_from('<I',raw,at)[0];v=np.frombuffer(raw,dtype=dtype,count=3,offset=at+4)
        x0=max(0,int(np.floor(min(v['x']))));x1=min(999,int(np.ceil(max(v['x']))))
        y0=max(0,int(np.floor(min(v['y']))));y1=min(849,int(np.ceil(max(v['y']))))
        if x0>x1 or y0>y1:continue
        den=(v['y'][1]-v['y'][2])*(v['x'][0]-v['x'][2])+(v['x'][2]-v['x'][1])*(v['y'][0]-v['y'][2])
        if abs(den)<1e-6:continue
        y,x=np.mgrid[y0:y1+1,x0:x1+1];x=x+.5;y=y+.5
        a=((v['y'][1]-v['y'][2])*(x-v['x'][2])+(v['x'][2]-v['x'][1])*(y-v['y'][2]))/den
        b=((v['y'][2]-v['y'][0])*(x-v['x'][2])+(v['x'][0]-v['x'][2])*(y-v['y'][2]))/den
        weights=np.stack([a,b,1-a-b],axis=-1);mask=np.all(weights>=0,axis=-1)
        if not mask.any():continue
        tex=textures[texture];th,tw=tex.shape[:2]
        u=np.clip(weights@v['u']*tw-.5,0,tw-1);t=np.clip(weights@v['v']*th-.5,0,th-1)
        ix=u.astype(int);iy=t.astype(int);fx=(u-ix)[...,None];fy=(t-iy)[...,None]
        sample=(tex[iy,ix]*(1-fx)+tex[iy,np.minimum(ix+1,tw-1)]*fx)*(1-fy)+(tex[np.minimum(iy+1,th-1),ix]*(1-fx)+tex[np.minimum(iy+1,th-1),np.minimum(ix+1,tw-1)]*fx)*fy
        colors=np.stack([(v['col']>>shift)&255 for shift in (0,8,16,24)],axis=-1)
        rgba=sample*(weights@colors)/255;alpha=(rgba[:,:,3]/255*mask)[...,None]
        dest=canvas[y0:y1+1,x0:x1+1];dest[:]=rgba[:,:,:3]*alpha+dest*(1-alpha)
    Image.fromarray(canvas.clip(0,255).astype(np.uint8)).save(out/name)

render('wheel-companion.png')
for mode,label,time in ((0,'opening',.10),(4,'focus-transition',.60),(4,'relax',1.5)):
    subprocess.run([str(exe),str(mode),str(time)],cwd=root,check=True)
    render(f'wheel-{label}.png')
print(out)
