#include "victory_encounter.h"
#include <cstdlib>
#include <iostream>
#include <limits>

using namespace Wayfarer::Victory;

int checks{};
void Check(bool value,const char* message) {
    ++checks;
    if(!value) {
        std::cerr<<"FAIL: "<<message<<'\n';
        std::exit(1);
    }
}

int main()
{
    {
        Encounter encounter;
        Check(!encounter.active && encounter.quiet==0,"new encounter starts idle");
        encounter.ObserveEnemy(0);
        encounter.ObserveParticipant(0);
        encounter.MarkDefeated(0);
        Check(encounter.enemies.empty() && encounter.defeated.empty() && encounter.participants.empty(),
            "zero IDs are ignored");
        Check(!encounter.active,"zero enemy does not start an encounter");
        Check(encounter.Tick(10,false)==Result::None && encounter.quiet==0,"idle time does not advance");
        encounter.ObserveParticipant(100);
        encounter.ObserveParticipant(100);
        Check(encounter.participants.size()==1 && encounter.participants.contains(100),"participants are unique");
        Check(!encounter.active && encounter.enemies.empty(),"participants alone do not establish enemies or combat");
        Check(encounter.Tick(.5F,true)==Result::None && encounter.active && encounter.quiet==0,
            "party combat starts an encounter without a known enemy");
        Check(encounter.Tick(10,true)==Result::None && encounter.quiet==0,"ongoing combat never settles");
        Check(encounter.Tick(1.25F,false)==Result::Finished,"combat without known enemies is not a victory");
    }

    for(std::uint32_t count:{4U,5U}) {
        Encounter encounter;
        encounter.ObserveParticipant(100);
        for(std::uint32_t id=1;id<=count;++id) {
            encounter.ObserveEnemy(id);
            encounter.MarkDefeated(id);
        }
        Check(encounter.active,"observing enemies starts an encounter");
        Check(encounter.Tick(.5F,false)==Result::None,"confirmed deaths do not fire immediately");
        Check(encounter.Tick(.5F,false)==Result::None,"one second of quiet is insufficient");
        Check(encounter.Tick(.125F,false)==Result::None,"less than 1.25 seconds never fires");
        const Result expected=count==5 ? Result::Victory : Result::Finished;
        Check(encounter.Tick(.125F,false)==expected,"four enemies finish; five defeated enemies win at 1.25 seconds");
        Check(!encounter.active,"result deactivates the encounter before returning");
        Check(encounter.enemies.size()==count && encounter.defeated.size()==count && encounter.participants.contains(100),
            "result retains encounter data for the caller");
        for(int repeat=0;repeat<3;++repeat)
            Check(encounter.Tick(2,false)==Result::None && encounter.quiet==1.25F,"each result fires only once");
        encounter.Reset();
        Check(encounter.enemies.empty() && encounter.defeated.empty() && encounter.participants.empty(),
            "caller reset after a result clears every set");
        Check(!encounter.active && encounter.quiet==0,"caller reset clears activity and quiet time");
    }

    {
        Encounter encounter;
        for(int transition=0;transition<10;++transition) {
            for(std::uint32_t id=1;id<=4;++id) {
                encounter.ObserveEnemy(id);
                encounter.MarkDefeated(id);
                encounter.MarkDefeated(id);
            }
            Check(encounter.Tick(.25F,true)==Result::None,"repeated combat transitions resume the same encounter");
            Check(encounter.Tick(.5F,false)==Result::None,"short combat gaps do not finish an encounter");
        }
        Check(encounter.enemies.size()==4 && encounter.defeated.size()==4,"repeated observations and deaths count each enemy once");
        Check(encounter.Tick(.75F,false)==Result::Finished,"repeated transitions cannot turn four enemies into a victory");
    }

    {
        Encounter encounter;
        for(std::uint32_t first:{1U,4U}) {
            for(std::uint32_t id=first;id<first+3;++id) {
                encounter.ObserveEnemy(id);
                encounter.MarkDefeated(id);
            }
            Check(encounter.enemies.size()==3 && encounter.defeated.size()==3,"separate fights contain only their own enemies");
            Check(encounter.Tick(1.25F,false)==Result::Finished,"two three-enemy fights never combine into a victory");
            encounter.Reset();
        }
    }

    {
        Encounter encounter;
        for(std::uint32_t id=1;id<=5;++id) {
            encounter.ObserveEnemy(id);
            encounter.MarkDefeated(id);
        }
        Check(encounter.Tick(1,false)==Result::None,"quiet countdown starts");
        Check(encounter.Tick(.25F,true)==Result::None && encounter.quiet==0,"resumed combat resets quiet time");
        Check(encounter.enemies.size()==5 && encounter.defeated.size()==5,"resuming combat preserves the encounter");
        Check(encounter.Tick(1,false)==Result::None,"old quiet time does not cause a premature victory");
        Check(encounter.Tick(.25F,false)==Result::Victory,"victory requires a full quiet interval after combat resumes");
    }

    {
        Encounter encounter;
        encounter.MarkDefeated(5);
        encounter.MarkDefeated(99);
        Check(encounter.defeated.empty() && !encounter.active,"unknown deaths neither count nor start an encounter");
        for(std::uint32_t id=1;id<=5;++id)encounter.ObserveEnemy(id);
        for(std::uint32_t id=1;id<=4;++id)encounter.MarkDefeated(id);
        encounter.MarkDefeated(99);
        Check(encounter.defeated.size()==4 && !encounter.defeated.contains(5),"a death before observation is not credited later");
        Check(encounter.Tick(1.25F,false)==Result::Finished,"an unknown death cannot replace a missing enemy death");
    }

    for(std::uint32_t confirmedDeaths:{0U,4U}) {
        Encounter encounter;
        for(std::uint32_t id=1;id<=5;++id)encounter.ObserveEnemy(id);
        for(std::uint32_t id=1;id<=confirmedDeaths;++id)encounter.MarkDefeated(id);
        Check(encounter.Tick(2,false)==Result::Finished,"fleeing or unloaded enemies prevent victory after quiet settles");
        Check(encounter.enemies.size()==5,"ending combat does not discard unconfirmed enemies");
        for(std::uint32_t id=1;id<=5;++id)encounter.MarkDefeated(id);
        Check(encounter.Tick(2,false)==Result::None && !encounter.active,"late deaths cannot fire a second result");
    }

    {
        Encounter encounter;
        encounter.enemies={1,2,3,4,5};
        encounter.defeated={1,2,3,4,99};
        encounter.active=true;
        Check(encounter.Tick(1.25F,false)==Result::Finished,"equal set sizes are insufficient when one enemy is undefeated");
    }

    {
        Encounter encounter;
        encounter.ObserveEnemy(1);
        encounter.MarkDefeated(1);
        encounter.ObserveParticipant(100);
        Check(encounter.Tick(.5F,false)==Result::None,"active encounter can be reset during quiet time");
        encounter.Reset();
        encounter.Reset();
        Check(encounter.enemies.empty() && encounter.defeated.empty() && encounter.participants.empty(),"reset is idempotent");
        Check(!encounter.active && encounter.quiet==0 && encounter.Tick(2,false)==Result::None,"reset cancels a pending result");
        encounter.ObserveEnemy(1);
        Check(encounter.defeated.empty(),"reusing an enemy ID after reset requires a new confirmed death");
        Check(encounter.Tick(1,false)==Result::None,"a new encounter receives its full quiet interval");
    }

    {
        const float invalidTimes[]={0,-.25F,std::numeric_limits<float>::quiet_NaN(),
            std::numeric_limits<float>::infinity(),-std::numeric_limits<float>::infinity()};
        Encounter encounter;
        for(float dt:invalidTimes)for(bool fighting:{false,true}) {
            Check(encounter.Tick(dt,fighting)==Result::None,"invalid time produces no idle result");
            Check(!encounter.active && encounter.quiet==0,"invalid time cannot start combat or advance an idle timer");
        }
        for(std::uint32_t id=1;id<=5;++id) {
            encounter.ObserveEnemy(id);
            encounter.MarkDefeated(id);
        }
        encounter.ObserveParticipant(100);
        Check(encounter.Tick(1,false)==Result::None,"valid time advances the quiet timer");
        for(float dt:invalidTimes)for(bool fighting:{false,true}) {
            Check(encounter.Tick(dt,fighting)==Result::None,"invalid time cannot finish an active encounter");
            Check(encounter.active && encounter.quiet==1,"invalid time neither advances nor resets quiet time");
            Check(encounter.enemies.size()==5 && encounter.defeated.size()==5 && encounter.participants.contains(100),
                "invalid time preserves encounter sets");
        }
        Check(encounter.Tick(.25F,false)==Result::Victory,"valid time resumes after invalid updates");
    }

    {
        Encounter encounter;
        for(std::uint32_t id=1;id<=5;++id) {
            encounter.ObserveEnemy(id);
            encounter.MarkDefeated(id);
        }
        Check(encounter.Tick(1,false)==Result::None,"quiet begins after the first enemies die");

        encounter.ObserveEnemy(6);
        encounter.MarkDefeated(6);
        Check(encounter.quiet==0,"a newly observed opponent restarts settling even between updates");
        Check(encounter.Tick(.25F,false)==Result::None,"a short intervening skirmish prevents early celebration");
        Check(encounter.Tick(1,false)==Result::Victory,"all six enemies require a fresh quiet interval");
    }

    std::cout<<checks<<" victory encounter checks passed\n";
}
