#include "follower_catchup.h"
#include "order_wheel.h"
#include <cstdlib>
#include <iostream>
#include <limits>
using namespace Wayfarer;
void Check(bool v,const char* message){if(!v){std::cerr<<message<<'\n';std::exit(1);}}
int main(){
 FollowerCatchup c;
 for(int i=0;i<19;++i)Check(!c.Update(.1F,true,4500,4000),"must remain distant for two seconds");
 Check(c.Update(.11F,true,4500,4000),"sustained separation recalls");
 c.Attempt(true);
 for(int i=0;i<149;++i)Check(!c.Update(.1F,true,4500,4000),"cooldown prevents repeated recalls");
 Check(c.Update(.2F,true,4500,4000),"recall available after cooldown");
 c.Attempt(false);
 Check(!c.Update(1,true,4500,4000),"failed landing backs off");
 Check(!c.Update(1,false,4500,4000),"unsafe state clears delay");
 Check(!c.Update(1,true,4500,4000),"resumption earns a fresh delay");
 Check(!c.Update(1,true,3999,4000),"returning within distance cancels recall");
 Check(!c.Update(1,true,std::numeric_limits<float>::quiet_NaN(),4000),"bad position never recalls");
 Check(!c.Update(1,true,4500,4000),"bad position reset delay");
 Check(c.Update(1,true,4500,4000),"valid distance eventually recalls");
 Wheel::Motion m;m.Open(0);
 float last=0;
 for(int i=0;i<40;++i){m.Update(.01F,0);Check(m.visibility>=last&&m.visibility<=1,"opening is monotonic and bounded");last=m.visibility;}
 m.Update(.016F,3);Check(m.centerWeight[0]>0&&m.centerWeight[3]>0,"center crossfades instead of switching");
 float sum=0;for(auto weight:m.centerWeight)sum+=weight;Check(std::abs(sum-1)<.0001F,"center maintains opacity through transitions");
 m.Close();last=m.visibility;
 for(int i=0;i<20;++i){m.Close();m.Update(.01F,3);Check(m.visibility<=last&&m.visibility>=0,"repeated cancel never restarts close");last=m.visibility;}
 Check(m.Finished()&&m.visibility==0,"exit reaches invisible before closing");
 m.Open(1);m.Update(.01F,1);m.Close();m.Update(.01F,1);Check(m.visibility<.1F,"cancel during opening does not flash to full opacity");
 m.Open(0);Check(!m.closing&&!m.Finished(),"reopening resets close state");
 Wheel::Motion a,b;a.Open(0);b.Open(0);
 for(int i=0;i<30;++i)a.Update(1.0F/30,1);
 for(int i=0;i<144;++i)b.Update(1.0F/144,1);
 Check(std::abs(a.highlight[1]-b.highlight[1])<.0001F,"focus smoothing is independent of refresh rate");
 a.Open(0);a.Update(.016F,1);Check(Wheel::Difference(a.angle,Wheel::Angle(0))<.4F,"indicator takes the short path across angle wrap");
 std::cout<<"Catch-up timing and wheel motion checks passed\n";
}
