#pragma once
#include "hand_hold_state.h"
#include "hand_hold_approach.h"
#include "travel_navigation.h"

namespace Wayfarer::HandHolding {

    std::string ReferenceKey(RE::Actor& actor);
    void Install();
    void Reset();
    void ReleaseActor(RE::FormID actor);
    bool BeginFrame(float dt,bool permitted,bool paused,const Tuning& tuning);
    void UpdatePartner(RE::PlayerCharacter& player,RE::Actor* partner,float dt,const TravelNavigation& navigation);
    bool IsAttached(RE::FormID actor);
    struct Approach { RE::FormID actor{};int side{1};float spacing{40};bool closing{};IK::Point velocity{};float heading{}; };
    Approach GetApproach();
}
