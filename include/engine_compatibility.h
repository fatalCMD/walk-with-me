#pragma once
#include "RE/Skyrim.h"
#include "RE/M/MenuTopicManager.h"

namespace Wayfarer::Engine
{
    inline bool IsKeyPressed(const RE::BSWin32KeyboardDevice& keyboard, std::uint32_t key)
    {

#ifdef WAYFARER_MODERN_COMMONLIB
        const auto& state = keyboard.GetRuntimeData().curState;
#else
        // Legacy CommonLib swaps the current/previous buffer names.
        const auto& state = keyboard.prevState;
#endif
        return key < sizeof(state) && (state[key] & 0x80) != 0;
    }

    template<class Callback>
    void ForEachHighActor(RE::ProcessLists& lists, Callback callback)
    {
#ifdef WAYFARER_MODERN_COMMONLIB
        lists.ForEachHighActor([&](RE::Actor* actor) {
            return actor ? callback(*actor) : RE::BSContainer::ForEachResult::kContinue;
        });
#else
        lists.ForEachHighActor(callback);
#endif
    }

    template<class Callback>
    void ForEachReferenceInRange(RE::TESObjectCELL& cell, const RE::NiPoint3& center, float radius, Callback callback)
    {
#ifdef WAYFARER_MODERN_COMMONLIB
        cell.ForEachReferenceInRange(center, radius, [&](RE::TESObjectREFR* reference) {
            return reference ? callback(*reference) : RE::BSContainer::ForEachResult::kContinue;
        });
#else
        cell.ForEachReferenceInRange(center, radius, callback);
#endif
    }

    inline void SetHeading(RE::Actor& actor, float angle)
    {
#ifdef WAYFARER_MODERN_COMMONLIB
        actor.SetHeading(angle);
#else
        actor.SetRotationZ(angle);
#endif
    }

    inline bool IsDialogueTransition(const RE::MenuTopicManager& topics)
    {
#ifdef WAYFARER_MODERN_COMMONLIB
        return topics.isGreetingPlayer || topics.forceGoodbye;
#else
        return topics.isGreetingPlayer || topics.isSayingGoodbye;
#endif
    }

    inline void Notify(const char* text)
    {
#ifdef WAYFARER_MODERN_COMMONLIB
        RE::SendHUDMessage::ShowHUDMessage(text);
#else
        RE::DebugNotification(text);
#endif
    }
}
