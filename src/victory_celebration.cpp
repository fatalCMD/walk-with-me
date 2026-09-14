#include "formation_controller.h"
#include "RE/C/CombatGroup.h"
#include "RE/M/MiddleHighProcessData.h"
#include "RE/T/TESCombatEvent.h"
#include "RE/T/TESDeathEvent.h"

namespace
{
    struct BattleEvent {
        RE::ActorHandle actor, target;
        RE::FormID dying{};
    };

    class BattleEvents final : public RE::BSTEventSink<RE::TESCombatEvent>, public RE::BSTEventSink<RE::TESDeathEvent>
    {
    public:
        static BattleEvents& Get() { static BattleEvents instance; return instance; }
        void Register()
        {
            if (registered) return;
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) {
                source->AddEventSink<RE::TESCombatEvent>(this);
                source->AddEventSink<RE::TESDeathEvent>(this);
                registered = true;
            }
        }
        RE::BSEventNotifyControl ProcessEvent(const RE::TESCombatEvent* event, RE::BSTEventSource<RE::TESCombatEvent>*) override
        {
            if (event && event->newState != RE::ACTOR_COMBAT_STATE::kNone) {
                auto* actor = event->actor ? event->actor->As<RE::Actor>() : nullptr;
                auto* target = event->targetActor ? event->targetActor->As<RE::Actor>() : nullptr;
                if (actor && target) Push({actor->GetHandle(), target->GetHandle(), 0});
            }
            return RE::BSEventNotifyControl::kContinue;
        }
        RE::BSEventNotifyControl ProcessEvent(const RE::TESDeathEvent* event, RE::BSTEventSource<RE::TESDeathEvent>*) override
        {
            if (event && event->dead && event->actorDying) Push({{}, {}, event->actorDying->GetFormID()});
            return RE::BSEventNotifyControl::kContinue;
        }
        std::vector<BattleEvent> Drain(bool& lost)
        {
            std::lock_guard lock(mutex);
            lost = std::exchange(overflow, false);
            return std::exchange(events, {});
        }
        void Clear() { bool ignored; (void)Drain(ignored); }
    private:
        void Push(BattleEvent event)
        {
            std::lock_guard lock(mutex);
            if (events.size() < 512) events.push_back(event);
            else overflow = true;  
        }
        std::mutex mutex;
        std::vector<BattleEvent> events;
        bool registered{}, overflow{};
    };

    bool SameSpace(RE::Actor& actor, RE::PlayerCharacter& player)
    {
        auto* a = actor.GetParentCell();
        auto* b = player.GetParentCell();
        return a && b && (a == b || (!a->IsInteriorCell() && !b->IsInteriorCell() && actor.GetWorldspace() == player.GetWorldspace()));
    }

    bool Speaking(RE::Actor& actor)
    {
        RE::TESConditionItem condition;
        condition.data.functionData.function = RE::FUNCTION_DATA::FunctionID::kIsTalking;
        condition.data.comparisonValue.f = 1;
        condition.data.flags.opCode = RE::CONDITION_ITEM_DATA::OpCode::kEqualTo;
        condition.data.object = RE::CONDITIONITEMOBJECT::kSelf;
        RE::ConditionCheckParams params{&actor, &actor};
        return condition.IsTrue(params);
    }

    bool OwnsIdle(RE::Actor& actor, RE::TESIdleForm* idle)
    {
        auto* process = actor.GetActorRuntimeData().currentProcess;
        return idle && process && process->middleHigh && process->middleHigh->lastIdlePlayed == idle;
    }

    bool InBattle(RE::Actor& actor)
    {
        return actor.IsInCombat() || actor.GetActorRuntimeData().boolBits.all(RE::Actor::BOOL_BITS::kSearchingInCombat);
    }

    bool PlayCelebration(RE::Actor& actor, RE::TESIdleForm* idle)
    {
        auto* process = actor.GetActorRuntimeData().currentProcess;
#ifdef WAYFARER_MODERN_COMMONLIB
        return process->PlayIdle(&actor, idle, nullptr);
#else

        using Function = bool (*)(RE::AIProcess*, RE::Actor*, RE::DEFAULT_OBJECT, RE::TESIdleForm*, bool, bool, RE::TESObjectREFR*);
        static REL::Relocation<Function> play{RELOCATION_ID(38290, 39256)};
        return play(process, &actor, RE::DEFAULT_OBJECT::kActionIdle, idle, true, false, nullptr);
#endif
    }

    bool StopCelebration(RE::Actor& actor, RE::TESIdleForm* idle)
    {

        if (!actor.Is3DLoaded() || actor.IsDead() || !OwnsIdle(actor, idle)) return true;
        if (InBattle(actor) || actor.GetCurrentScene() || actor.GetOccupiedFurniture().get() || Speaking(actor)) return false;
#ifdef WAYFARER_MODERN_COMMONLIB
        actor.GetActorRuntimeData().currentProcess->StopCurrentIdle(&actor, true);
#else
        using Function = void (*)(RE::AIProcess*, RE::Actor*, bool);
        static REL::Relocation<Function> stop{RELOCATION_ID(38291, 39257)};
        stop(actor.GetActorRuntimeData().currentProcess, &actor, true);
#endif
        return true;
    }

    constexpr float reactionSeconds = 2.6F;
    constexpr float startWindowSeconds = 4.0F;
}

namespace Wayfarer
{
    void FormationController::InitializeVictoryEvents() { BattleEvents::Get().Register(); }

    void FormationController::ReportAliasSync(bool busy)
    {
        std::lock_guard lock(stateMutex);
        aliasSyncBusy = busy;
    }

    void FormationController::UpdateVictoryCleanup()
    {
        if (auto* ui = RE::UI::GetSingleton(); ui && ui->GameIsPaused()) return;
        std::erase_if(victoryCleanup, [](const VictoryReaction& reaction) {
            auto actor = reaction.actor.get();
            return !actor || StopCelebration(*actor, reaction.idle);
        });
    }

    void FormationController::ResetVictoryCelebration(bool stopAnimations)
    {
        if (stopAnimations) {
            for (const auto& reaction : victoryReactions) {
                if (auto actor = reaction.actor.get(); actor && reaction.started && !StopCelebration(*actor, reaction.idle))
                    victoryCleanup.push_back(reaction);
            }
        } else victoryCleanup.clear();  
        victoryReactions.clear();
        victoryEncounter.Reset();
        victoryEnemies.clear();
        victoryScanTimer = 0;
        BattleEvents::Get().Clear();
    }

    bool FormationController::VictoryActorReady(RE::Actor& actor, RE::PlayerCharacter& player, bool starting) const
    {
        const auto id = actor.GetFormID();
        if (!managed.contains(id) || explicitExclusions.contains(id) || !UsabilityRejection(actor, player).empty() ||
            !SameSpace(actor, player) || !actor.Is3DLoaded() || InBattle(actor) || actor.GetCurrentScene() ||
            Speaking(actor) || actor.IsInKillMove() || actor.IsInMidair() || actor.IsInRagdollState() ||
            actor.GetOccupiedFurniture().get() || actor.IsSneaking()) return false;
        auto* state = actor.AsActorState();
        if (!state || state->IsWeaponDrawn() || state->GetSitSleepState() != RE::SIT_SLEEP_STATE::kNormal ||
            state->IsFlying() || state->IsBleedingOut() || state->IsUnconscious()) return false;
        auto* npc = RE::TESForm::LookupByID<RE::BGSKeyword>(0x13794);  
        if (!npc || !actor.GetRace() || !actor.GetRace()->HasKeyword(npc)) return false;
        const auto offset = actor.GetPosition() - player.GetPosition();
        if (offset.Length() > 900.0F || std::abs(offset.z) > 180.0F) return false;
        if (starting) {

            const auto* alias = GetRefAlias(questCache, FollowerAlias(managed.at(id).slot));
            if (aliasSyncBusy || (alias && alias->GetReference() == &actor)) return false;
            for (const auto& cleanup : victoryCleanup) if (cleanup.actor == actor.GetHandle()) return false;
            bool driven = false;
            actor.GetGraphVariableBool("bAnimationDriven", driven);
            RE::NiPoint3 velocity{};
            actor.GetLinearVelocity(velocity);
            if (driven || velocity.Length() > 30.0F) return false;
        }
        const auto* process = actor.GetActorRuntimeData().currentProcess;
        return process && process->middleHigh;
    }

    void FormationController::UpdateVictoryCelebration(RE::PlayerCharacter& player, float dt)
    {
        const auto& settings = Settings::GetSingleton().Get();
        auto* ui = RE::UI::GetSingleton();
        auto* state = player.AsActorState();
        auto* controls = RE::ControlMap::GetSingleton();
        if (!enabled || !settings.victoryCelebrations || player.IsDead() || !state ||
            (ui && (ui->IsMenuOpen(RE::LoadingMenu::MENU_NAME) || ui->IsMenuOpen(RE::MainMenu::MENU_NAME)))) {
            ResetVictoryCelebration(); return;
        }
        std::vector<RE::NiPointer<RE::Actor>> followers;
        std::unordered_set<RE::FormID> party{player.GetFormID()};
        bool fighting = InBattle(player);
        for (const auto& [id, follower] : managed) {
            auto actor = follower.handle.get();
            if (!actor || actor->IsDead() || actor->IsDisabled() || !actor->Is3DLoaded() ||
                explicitExclusions.contains(id) || !SameSpace(*actor, player) ||
                (!IsRegisteredFollower(id) && CandidateRejection(*actor))) continue;
            party.insert(id);
            followers.push_back(actor);
            if (InBattle(*actor)) { fighting = true; victoryEncounter.ObserveParticipant(id); }
        }
        auto observeEnemy = [&](RE::Actor& actor) {
            if (party.contains(actor.GetFormID()) || actor.IsPlayerTeammate()) return;
            victoryEncounter.ObserveEnemy(actor.GetFormID());
            victoryEnemies[actor.GetFormID()] = actor.GetHandle();
            if (actor.IsDead()) victoryEncounter.MarkDefeated(actor.GetFormID());
        };
        bool lostEvents = false;
        const auto events = BattleEvents::Get().Drain(lostEvents);
        if (lostEvents) { ResetVictoryCelebration(); return; }
        for (const auto& event : events) {
            if (event.dying) { victoryEncounter.MarkDefeated(event.dying); continue; }
            auto actor = event.actor.get();
            auto target = event.target.get();
            if (!actor || !target) continue;
            const bool actorParty = party.contains(actor->GetFormID());
            const bool targetParty = party.contains(target->GetFormID());
            if (actorParty == targetParty) continue;
            auto& member = actorParty ? *actor : *target;
            auto& enemy = actorParty ? *target : *actor;
            if (enemy.IsPlayerTeammate()) continue;

            fighting = true;
            observeEnemy(enemy);
            if (!member.IsPlayerRef()) victoryEncounter.ObserveParticipant(member.GetFormID());
        }

        victoryScanTimer += dt;
        if (victoryScanTimer >= .2F) {
            victoryScanTimer = 0;
            auto collectTargets = [&](RE::Actor& member) {
                auto* group = member.GetCombatGroup();
                if (!group || !InBattle(member)) return;
                fighting = true;  
                if (!member.IsPlayerRef()) victoryEncounter.ObserveParticipant(member.GetFormID());
                std::vector<RE::ActorHandle> targets;
                {
                    RE::BSReadLockGuard guard(group->lock);
                    for (const auto& target : group->targets) targets.push_back(target.targetHandle);
                }
                for (auto handle : targets) if (auto actor = handle.get(); actor && !actor->IsDead()) observeEnemy(*actor);
            };
            collectTargets(player);
            for (const auto& actor : followers) collectTargets(*actor);
        }
        for (const auto& [id, handle] : victoryEnemies) {
            if (auto enemy = handle.get()) {
                if (enemy->IsDead()) victoryEncounter.MarkDefeated(id);
                else victoryEncounter.defeated.erase(id);  
            }
        }

        RE::NiPoint3 velocity{};
        player.GetLinearVelocity(velocity);
        const bool canCelebrate = !player.IsSneaking() && !player.IsOnMount() && !state->IsSwimming() &&
            !state->IsBleedingOut() && !player.IsInKillMove() && !player.IsInMidair() && !player.GetCurrentScene() &&
            (!controls || controls->IsMovementControlsEnabled()) && velocity.Length() < 180.0F;
        if (fighting || !canCelebrate) {
            for (const auto& reaction : victoryReactions) if (auto actor = reaction.actor.get(); actor && reaction.started && !StopCelebration(*actor, reaction.idle))
                victoryCleanup.push_back(reaction);
            victoryReactions.clear();
        }

        const auto outcome = victoryEncounter.Tick(dt, fighting);
        if (outcome != Victory::Result::None) {
            if (outcome == Victory::Result::Victory && canCelebrate) {
                ++victorySequence;
                std::sort(followers.begin(), followers.end(), [](const auto& a, const auto& b) { return a->GetFormID() < b->GetFormID(); });
                for (const auto& actor : followers) {
                    if (!victoryEncounter.participants.contains(actor->GetFormID())) continue;
                    const auto variation = RestPose::Mix(actor->GetFormID() + victorySequence * 7919);

                    constexpr RE::FormID idles[]{0xD8730, 0xD8733, 0xF7C8C};
                    auto* idle = RE::TESForm::LookupByID<RE::TESIdleForm>(idles[variation % std::size(idles)]);
                    if (idle) victoryReactions.push_back({actor->GetHandle(), idle, .4F + (variation % 7) * .1F});
                }
                logger::info("[Victory] {} distinct enemies defeated; {} participating companions queued", victoryEncounter.enemies.size(), victoryReactions.size());
            }
            victoryEncounter.Reset();
            victoryEnemies.clear();
        }

        std::erase_if(victoryReactions, [&](VictoryReaction& reaction) {
            auto actor = reaction.actor.get();
            if (!actor) return true;
            reaction.elapsed += dt;
            if (!reaction.started) {
                if (reaction.elapsed > startWindowSeconds) return true;
                if (reaction.elapsed < reaction.delay || !VictoryActorReady(*actor, player, true)) return false;
                if (!PlayCelebration(*actor, reaction.idle)) return true;
                reaction.started = true;
                reaction.elapsed = 0;
                logger::info("[Victory] {} plays {:08X} for at most {:.1f}s", actor->GetName(), reaction.idle->GetFormID(), reactionSeconds);
                return false;
            }
            if (!OwnsIdle(*actor, reaction.idle)) return true;
            if (reaction.elapsed >= reactionSeconds || !VictoryActorReady(*actor, player, false)) {
                if (!StopCelebration(*actor, reaction.idle)) victoryCleanup.push_back(reaction);
                return true;
            }
            return false;
        });
    }
}
