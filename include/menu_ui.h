#pragma once
#include "config.h"

namespace Wayfarer
{
    enum class PartyOrder { kTravel, kScout, kRear, kRoam };
    struct CompanionView
    {
        RE::FormID id{};
        std::string name;
        std::string state;
        std::string personalityKey, personality;
        std::string handHoldKey;
        int personalityOverride{-1};
        bool managed{}, excluded{}, nff{}, manuallyAdded{}, apiRegistered{}, eligible{};
    };
    struct PartyView
    {
        SettingsData settings;
        std::vector<CompanionView> party;
        std::string state{ "Load a save to see your party" };
        PartyOrder order{ PartyOrder::kTravel };
        FormationMode mode{ FormationMode::kDynamic };
        std::uint64_t generation{};
        bool inGame{}, gameplay{}, enabled{ true }, nffInstalled{};
        int activeCount{};
        bool sandboxActive{};
        float sandboxRadius{};
    };
    namespace Menu
    {
        void Register();
        void Publish();  
        void Reset();
        bool HandleInput(RE::InputEvent* a_event);
        bool IsInstalled();
    }
}
