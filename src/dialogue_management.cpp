#include "formation_controller.h"
#include "engine_compatibility.h"
#include "follower_dialogue.h"

namespace
{
    int DialogueFactionRank(RE::Actor& actor, RE::TESFaction* faction)
    {
#ifdef WAYFARER_MODERN_COMMONLIB
        return actor.GetFactionRank(faction, false);
#else

        using Function = std::int32_t (*)(RE::Actor*, RE::TESFaction*, bool);
        static REL::Relocation<Function> function{ REL::RelocationID(36668, 37676) };
        return function(&actor, faction, false);
#endif
    }
    void RemoveDialogueFaction(RE::Actor& actor, RE::TESFaction* faction)
    {
#ifdef WAYFARER_MODERN_COMMONLIB
        actor.RemoveFromFaction(faction);
#else
        using Function = void (*)(RE::Actor*, RE::TESFaction*);
        static REL::Relocation<Function> function{ REL::RelocationID(36680, 37688) };
        function(&actor, faction);
#endif
    }
}

namespace Wayfarer
{
    bool FormationController::IsDialogueFollower(RE::Actor& actor) const
    {
        if (actor.IsPlayerRef() || actor.IsDead() || actor.IsDisabled()) return false;
        const auto waiting = actor.AsActorValueOwner()->GetActorValue(RE::ActorValue::kWaitingForPlayer);
        if (!std::isfinite(waiting) || waiting < 0.0F) return false;

        if (IsCustomFollower(actor)) return actor.IsPlayerTeammate();
        auto* faction = RE::TESForm::LookupByID<RE::TESFaction>(0x5C84E);
        return actor.IsPlayerTeammate() || IsNFFFollower(actor) || (faction && actor.IsInFaction(faction));
    }

    bool FormationController::IsRegisteredFollower(RE::FormID id) const
    {
        if (manualRegistrations.contains(id)) return true;  
        if (!dialogueRegistrations.contains(id)) return false;
        auto* actor = RE::TESForm::LookupByID<RE::Actor>(id);
        return actor && IsDialogueFollower(*actor);
    }

    void FormationController::SyncFollowerDialogue(RE::Actor& actor)
    {
        auto* data = RE::TESDataHandler::GetSingleton();
        auto* faction = data ? data->LookupForm<RE::TESFaction>(0x880, Settings::GetSingleton().Get().pluginName) : nullptr;
        if (!faction) return;
        const auto id = actor.GetFormID();
        const auto rank = FollowerDialogueRank(dialogueRegistrations.contains(id), managed.contains(id),
            manualRegistrations.contains(id), explicitExclusions.contains(id), IsDialogueFollower(actor),
            enabled && mode != FormationMode::kVanilla);
        if (DialogueFactionRank(actor, faction) == rank) return;
        if (rank < 0) RemoveDialogueFaction(actor, faction);
        else actor.AddToFaction(faction, static_cast<std::int8_t>(rank));
    }

    void FormationController::UpdateFollowerDialogue(float dt)
    {
        dialogueRosterTimer -= dt;
        if (dialogueRosterTimer > 0) return;
        dialogueRosterTimer = 0.25F;
        if (auto* lists = RE::ProcessLists::GetSingleton()) {
            Engine::ForEachHighActor(*lists, [&](RE::Actor& actor) {
                SyncFollowerDialogue(actor);
                return RE::BSContainer::ForEachResult::kContinue;
            });
        }
    }

    void FormationController::SetDialogueManagement(RE::Actor* actor, bool add)
    {
        std::lock_guard lock(stateMutex);
        if (!actor || actor->IsPlayerRef()) return;
        const auto id = actor->GetFormID();
        if (add) {
            if (dialogueRegistrations.contains(id) || manualRegistrations.contains(id) ||
                (managed.contains(id) && !explicitExclusions.contains(id))) return;
            if (!IsDialogueFollower(*actor)) { Notify("This companion is no longer following you."); return; }
            if (!enabled || mode == FormationMode::kVanilla) { Notify("Enable Walk With Me before adding a companion."); return; }
            if (!managed.contains(id) && managed.size() >= static_cast<std::size_t>(Settings::GetSingleton().Get().maxFollowers)) {
                Notify("Walk With Me's companion limit has been reached."); return;
            }
            dialogueRegistrations.insert(id);
            explicitExclusions.erase(id);
            Notify("Companion added to Walk With Me.");
        } else {
            if (!dialogueRegistrations.erase(id)) return;  
            explicitExclusions.insert(id);  
            Notify("Companion removed from Walk With Me.");
        }

        scanTimer = Settings::GetSingleton().Get().scanInterval;
        SyncFollowerDialogue(*actor);
        logger::info("[Dialogue] {} manual management for {} ({:08X})", add ? "Enabled" : "Removed", actor->GetName(), id);
    }
}
