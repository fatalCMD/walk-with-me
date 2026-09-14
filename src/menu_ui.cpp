#include "menu_ui.h"
#include "hud_notice.h"
#include "order_wheel.h"
#include "order_visuals.h"
#include "command_gesture.h"
#include "engine_compatibility.h"
#include "formation_controller.h"
#include "SKSEMenuFramework.h"
#include <functional>
#include <optional>

namespace Wayfarer::Menu
{
    namespace
    {
        namespace Im = ImGuiMCP;
        namespace Draw = ImGuiMCP::ImDrawListManager;
        namespace MF = SKSEMenuFramework;
        using V = Im::ImVec2;
        constexpr auto teal = IM_COL32(201, 189, 156, 255);
        constexpr auto gold = IM_COL32(197, 180, 136, 255);
        constexpr auto ink = IM_COL32(19, 19, 18, 242);
        constexpr auto panel = IM_COL32(36, 35, 32, 220);
        constexpr auto muted = IM_COL32(149, 146, 137, 255);
        constexpr auto white = IM_COL32(222, 219, 207, 255);
        constexpr std::uint32_t unbound = 0xFFFFFFFF;
        std::mutex viewMutex;
        PartyView cached;
        std::atomic<bool> installed{}, refresh{ true };
        std::atomic<int> capturing{ -1 }, captured{ -1 }, applyResult{};
        std::atomic<bool> restoreHotkey{}, previousHotkey{};
        std::atomic<std::uint64_t> captureStarted{};
        MF::Model::WindowInterface* commandWindow{};
        bool wheelBlurOwned{};  
        std::atomic<bool> wheelCloseRequested{};
        void SyncWheelBlur()
        {
            const bool open = commandWindow && commandWindow->IsOpen;
            auto* blur = RE::UIBlurManager::GetSingleton();
            if (!blur || open == wheelBlurOwned) return;
            if (open) blur->IncrementBlurCount();
            else if (blur->blurCount) blur->DecrementBlurCount();
            wheelBlurOwned = open;
        }
        void QueueWheelBlur()
        {
            if (auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask([] { SyncWheelBlur(); });
        }
        void SetWheelOpen(bool open)
        {
            if (commandWindow) {
                wheelCloseRequested=!open;
                if(open)commandWindow->IsOpen=true;
            }

            QueueWheelBlur();
        }

        std::unique_ptr<MF::Model::InputEvent> inputRegistration;
        std::unique_ptr<MF::Model::HudElement> hudRegistration;
        std::unique_ptr<MF::Model::Event> eventRegistration;
        SettingsData draft;
        bool haveDraft{}, dirty{};
        std::mutex settingsMutex;
        std::optional<std::pair<std::uint64_t, SettingsData>> pendingSettings;
        bool settingsTaskQueued{};
        std::atomic<std::uint64_t> requestedRevision{}, appliedRevision{};
        std::string feedback;
        std::uint64_t nextPublish{}, hudPreviewAt{};
        bool hudPreviewEnabled{true};
        bool hudPreviewPanel{true};
        std::atomic<float> padX{},padY{};
        std::atomic<std::uint64_t> padStickAt{},orderNotice{};
        std::atomic<bool> padConfirm{},padCancel{},padUsed{};
        std::atomic<int> padStep{};
        std::uint32_t padHeld{};
        float hudPreviewScale{.8F},hudPreviewHeight{.32F};
        constexpr std::array<const char*, 6> profileNames{ "Natural", "Lead", "Companion", "Rear", "Relax", "Vanilla" };
        constexpr auto profileModes=OrderModes;
        constexpr std::array<const char*,6> styleHints{"Find your own space as we travel","Take the lead along our route","Travel at my side","Keep to the rear","Stay here and make yourselves at home","Return travel and rest to Skyrim or your follower framework"};
        std::uint32_t KeyboardModifiers()
        {
            auto* input = RE::BSInputDeviceManager::GetSingleton();
            auto* keyboard = input ? input->GetKeyboard() : nullptr;
            return Hotkeys::ReadModifiers([keyboard](std::uint32_t key) { return keyboard && Engine::IsKeyPressed(*keyboard, key); });
        }

        void CancelCapture()
        {
            capturing.store(-1);
            if (restoreHotkey.exchange(false)) { MF::SetHotkeyEnabled(previousHotkey.load()); }
        }
        void StartCapture(int row)
        {
            if (!restoreHotkey.exchange(true)) { previousHotkey.store(MF::IsHotkeyEnabled()); }
            MF::SetHotkeyEnabled(false);  
            captured.store(-1); captureStarted.store(GetTickCount64()); capturing.store(row);
        }

        PartyView Read()
        {
            std::lock_guard lock(viewMutex);
            return cached;
        }
        void Cache(PartyView value)
        {
            std::lock_guard lock(viewMutex);
            cached = std::move(value);
        }
        void Queue(std::function<void(FormationController&)> work)
        {
            if (auto* tasks = SKSE::GetTaskInterface()) {
                tasks->AddTask([work = std::move(work)] {
                    auto& c = FormationController::GetSingleton();
                    work(c);
                    Cache(c.Snapshot());
                });
            }
        }
        float E(float value) { return Im::GetFontSize() * value; }
        void Space(float value = 0.16F) { Im::Dummy({ 0, E(value) }); }
        void Note(const char* text)
        {
            Im::PushStyleColor(Im::ImGuiCol_Text, muted);
            Im::TextWrapped("%s", text);
            Im::PopStyleColor();
        }
        struct Inscription {
            bool pushed{};
            Inscription(){auto* before=Im::GetFont();const char* name=Im::ImFontManger::GetDebugName(before);if(name&&std::string_view(name).find("WalkWithMeInscription")!=std::string_view::npos)return;MF::PushFont("WalkWithMeInscription");pushed=Im::GetFont()!=before;}
            ~Inscription(){if(pushed)Im::PopFont();}
        };

        void Help(const char* text) { if (Im::IsItemHovered()) { Im::SetTooltip("%s", text); } }

        void Icon(Im::ImDrawList* draw, V c, float r, int type, Im::ImU32 color)
        {
            static const std::array<std::string,8> glyphs = [] {
                std::array<std::string,8> result;
                constexpr unsigned codes[]{0xf14e,0xf024,0xf132,0xf06d,0xf554,0xf0c0,0xf084,0xf007};
                for (int i=0;i<8;++i) result[i]=FontAwesome::UnicodeToUtf8(codes[i]);
                return result;
            }();
            FontAwesome::PushSolid();
            const auto& glyph=glyphs[std::clamp(type,0,7)];
            const float size=r*2.0F;
            const auto bounds=Im::CalcTextSize(glyph.c_str());
            const float ratio=size/Im::GetFontSize();
            Draw::AddText(draw,Im::GetFont(),size,{c.x-bounds.x*ratio*.5F,c.y-bounds.y*ratio*.5F},color,glyph.c_str());
            FontAwesome::Pop();
        }
        void Label(const char* text, int icon = 0)
        {
            Space(0.35F);
            const auto p = Im::GetCursorScreenPos();
            Icon(Im::GetWindowDrawList(), {p.x+E(.4F),p.y+E(.5F)}, E(.35F), icon, gold);
            Im::Dummy({E(1.05F),E(1)}); Im::SameLine(0,0);
            Im::PushStyleColor(Im::ImGuiCol_Text, gold); Im::TextUnformatted(text); Im::PopStyleColor();
            Im::Separator(); Space(.12F);
        }
        struct Theme
        {
            Theme()
            {
                Im::PushStyleColor(Im::ImGuiCol_Text, white);
                Im::PushStyleColor(Im::ImGuiCol_TextDisabled, muted);
                Im::PushStyleColor(Im::ImGuiCol_WindowBg, ink);
                Im::PushStyleColor(Im::ImGuiCol_ChildBg, ink);
                Im::PushStyleColor(Im::ImGuiCol_FrameBg, panel);
                Im::PushStyleColor(Im::ImGuiCol_Button, panel);
                Im::PushStyleColor(Im::ImGuiCol_ButtonHovered, IM_COL32(67, 63, 53, 230));
                Im::PushStyleColor(Im::ImGuiCol_ButtonActive, IM_COL32(92, 84, 64, 230));
                Im::PushStyleColor(Im::ImGuiCol_CheckMark, teal);
                Im::PushStyleColor(Im::ImGuiCol_SliderGrab, teal);
                Im::PushStyleColor(Im::ImGuiCol_Header, IM_COL32(67, 62, 49, 230));
                Im::PushStyleColor(Im::ImGuiCol_HeaderHovered, IM_COL32(86, 78, 60, 230));
                Im::PushStyleColor(Im::ImGuiCol_PopupBg, ink);
                Im::PushStyleVar(Im::ImGuiStyleVar_FramePadding, V{ E(0.2F), E(0.09F) });
                Im::PushStyleVar(Im::ImGuiStyleVar_ItemSpacing, V{ E(0.25F), E(0.12F) });
                Im::PushStyleVar(Im::ImGuiStyleVar_FrameRounding, 0.0F);
                Im::PushStyleVar(Im::ImGuiStyleVar_WindowPadding, V{ E(0.35F), E(0.25F) });
            }
            ~Theme() { Im::PopStyleVar(4); Im::PopStyleColor(13); }
        };
        std::string KeyName(std::uint32_t code)
        {
            if (code == unbound) { return "Unbound"; }
            char name[96]{};

            const LONG scan = static_cast<LONG>((code & 0x7F) << 16) | ((code & 0x80) ? (1 << 24) : 0);
            if (GetKeyNameTextA(scan, name, sizeof(name)) > 0) { return name; }
            return fmt::format("Key {}", code);
        }
        void Prepare(const PartyView& view)
        {

            if (!haveDraft) { draft = view.settings; haveDraft = true; }
            if (!dirty && appliedRevision.load() == requestedRevision.load()) {
                const int result = applyResult.load();
                if (result != 2 && capturing.load() < 0) { draft = Read().settings; }
                if (result == 2) { feedback = "Could not save settings. Check file access, then change the setting again."; }
            }
            const int key = captured.exchange(-1);
            const int row = capturing.load();
            if (row >= 0 && key >= 0) {
                if ((key & 255) != 1) {  
                    RebindHotkey(draft, row, Hotkeys::CapturedChord(key));
                    dirty = true;
                }
                CancelCapture();
            }
            if (capturing.load() >= 0 && GetTickCount64() - captureStarted.load() > 15000) { CancelCapture(); }
        }

        void Header(const PartyView& view, const char*)
        {
            Label("WALK WITH ME");
            bool enabled = draft.enabled;
            if (Im::Checkbox("Enabled", &enabled)) {
                draft.enabled = enabled;
                dirty = true;
            }
            Im::SameLine(); Im::TextDisabled("%s  |  %zu / %d companions", view.state.c_str(),
                std::count_if(view.party.begin(), view.party.end(), [](const auto& p) { return p.managed; }), view.settings.maxFollowers);
            Space();
        }
        void SaveChanges()
        {
            if (!dirty) { return; }
            auto* tasks = SKSE::GetTaskInterface();
            if (!tasks) { feedback = "Settings are unavailable until SKSE is ready."; return; }
            bool startTask = false;
            {
                std::lock_guard lock(settingsMutex);
                pendingSettings = std::make_pair(++requestedRevision, draft);
                startTask = !settingsTaskQueued;
                settingsTaskQueued = true;
            }
            dirty = false;
            feedback.clear();
            if (!startTask) { return; }

            tasks->AddTask([] {
                for (;;) {
                    std::optional<std::pair<std::uint64_t, SettingsData>> update;
                    {
                        std::lock_guard lock(settingsMutex);
                        if (!pendingSettings) { settingsTaskQueued = false; return; }
                        update = std::move(pendingSettings);
                        pendingSettings.reset();
                    }
                    auto& c = FormationController::GetSingleton();
                    const bool result = c.ApplyPreferences(update->second);
                    Cache(c.Snapshot());
                    applyResult.store(result ? 1 : 2);
                    appliedRevision.store(update->first);
                }
            });
        }
        void Footer()
        {
            SaveChanges();
            if (!feedback.empty()) { Note(feedback.c_str()); }
        }
        void IssueStyle(FormationMode value)
        {
            Queue([value](auto& c) { c.SetMode(value);++orderNotice;CommandGesture::Request(value); });
            SetWheelOpen(false);
        }

        void OrderCards(const PartyView& view)
        {
            Im::BeginDisabled(!view.inGame || !view.enabled);
            if (Im::BeginTable("orders", 3, Im::ImGuiTableFlags_SizingStretchSame)) {
                for (int i=0;i<Wheel::count;++i) {
                    Im::TableNextColumn();
                    if (Im::Button(profileNames[i], {-1,0})) { IssueStyle(profileModes[i]); }
                    Help(styleHints[i]);
                }
                Im::EndTable();
            }
            Im::EndDisabled();
        }
        void Roster(const PartyView& view)
        {
            Note("Nearby recruited followers appear here. Add companions here or through dialogue.");
            if(view.party.empty()){Note("No recruited followers detected nearby.");return;}
            if(Im::BeginTable("companions",4,Im::ImGuiTableFlags_RowBg|Im::ImGuiTableFlags_SizingStretchProp)){
                Im::TableSetupColumn("Companion",Im::ImGuiTableColumnFlags_WidthStretch);
                Im::TableSetupColumn("Status",Im::ImGuiTableColumnFlags_WidthStretch);
                Im::TableSetupColumn("Personality",Im::ImGuiTableColumnFlags_WidthFixed,E(8));
                Im::TableSetupColumn("Manage",Im::ImGuiTableColumnFlags_WidthFixed,E(5));Im::TableHeadersRow();
                for(const auto& row:view.party){
                    Im::PushID(static_cast<int>(row.id));Im::TableNextRow();Im::TableNextColumn();
                    Im::TextUnformatted(row.name.c_str());
                    if(Im::IsItemHovered()){Im::SetTooltip("%s\n%s%s",row.state.c_str(),row.personality.c_str(),row.nff?"\nManaged by NFF":"");}
                    Im::TableNextColumn();
                    Im::TextUnformatted(row.manuallyAdded?"Added manually":row.apiRegistered?"Managed by integration":row.managed&&!row.excluded?"Added automatically":row.excluded?"Removed":"Not added");
                    Help(row.state.c_str());
                    Im::TableNextColumn();Im::SetNextItemWidth(-1);
                    auto pref=draft.personalityOverrides.find(row.personalityKey);
                    int choice=pref==draft.personalityOverrides.end()?0:pref->second+1;
                    Im::BeginDisabled(!draft.personalities);
                    if(Im::Combo("##personality",&choice,"Automatic\0Balanced\0Sociable\0Curious\0Reserved\0Watchful\0")){
                        if(choice==0)draft.personalityOverrides.erase(row.personalityKey);else draft.personalityOverrides[row.personalityKey]=choice-1;dirty=true;
                    }
                    Help(row.personality.c_str());Im::EndDisabled();
                    Im::TableNextColumn();
                    const bool remove=row.manuallyAdded || (!row.excluded && row.managed);
                    Im::BeginDisabled(row.apiRegistered || (!remove && (!row.eligible || !view.enabled || view.mode==FormationMode::kVanilla)));
                    if(Im::Button(remove?"Remove":"Add",{-1,0})){
                        const auto id=row.id;const auto stamp=view.generation;const bool manual=row.manuallyAdded;
                        Queue([id,remove,manual,stamp](auto& c){
                            if(c.Snapshot().generation!=stamp)return;
                            if(remove&&!manual){(void)c.ExcludeFollower(id);return;}
                            c.SetDialogueManagement(RE::TESForm::LookupByID<RE::Actor>(id),!remove);
                        });
                    }
                    Help(row.apiRegistered?"This registration is owned by another integration.":remove?"Release Walk With Me's control and prevent automatic re-addition. This does not dismiss the follower.":"Allow Walk With Me to direct this companion's travel and relaxation. The choice is saved and can be removed here or in dialogue.");
                    Im::EndDisabled();Im::PopID();
                }
                Im::EndTable();
            }
        }
        void __stdcall RenderParty()
        {
            const auto view=Read();Prepare(view);Theme theme;
            Im::BeginChild("WalkWithMeParty",{0,0});Im::SetWindowFontScale(.70F);
            Header(view,"");OrderCards(view);Label("TRAVEL STYLE",5);
            for(int i=0;i<Wheel::count;++i){
                if(i%3)Im::SameLine();
                if(Im::RadioButton(profileNames[i],view.mode==profileModes[i])) {
                    const auto chosen=profileModes[i];Queue([chosen](auto& c){c.SetMode(chosen);});
                }
            }
            Note("Companions choose their own space as you travel.");
            Roster(view);
            Label("PARTY",5);
            Im::SetNextItemWidth(E(9));dirty|=Im::SliderInt("Companion limit",&draft.maxFollowers,1,PARTY_CAPACITY,"%d",Im::ImGuiSliderFlags_AlwaysClamp);
            dirty|=Im::Checkbox("Automatically add followers",&draft.autoDiscover);
            Help("Adds current and newly recruited followers as they load nearby. Remove keeps a follower excluded. Manual Add remains available when this is off.");
            Im::BeginDisabled(!draft.autoDiscover);
            Im::BeginDisabled(!view.nffInstalled);dirty|=Im::Checkbox("Include NFF followers automatically",&draft.enforceNFF);
            Help("Include active NFF followers in automatic enrollment.");Im::EndDisabled();
            dirty|=Im::Checkbox("Include custom followers automatically",&draft.enforceCustomFollowers);
            Help("Include recruited custom teammates in automatic enrollment. Detection is not a compatibility guarantee.");
            Im::EndDisabled();
            Footer();Im::EndChild();
        }
        void Slider(const char* name,float& value,float low,float high,const char* format,const char* hint)
        {
            Im::TableNextRow();Im::TableNextColumn();Im::TextUnformatted(name);Help(hint);
            Im::TableNextColumn();Im::SetNextItemWidth(-1);Im::PushID(name);
            dirty|=Im::SliderFloat("##value",&value,low,high,format,Im::ImGuiSliderFlags_AlwaysClamp);Help(hint);Im::PopID();
        }
        void Toggle(const char* name,bool& value,const char* hint)
        {
            Im::TableNextRow();Im::TableNextColumn();Im::TextUnformatted(name);Help(hint);
            Im::TableNextColumn();Im::PushID(name);dirty|=Im::Checkbox("##value",&value);Help(hint);Im::PopID();
        }
        bool Rows(const char* id)
        {
            if(!Im::BeginTable(id,2,Im::ImGuiTableFlags_SizingStretchSame|Im::ImGuiTableFlags_RowBg))return false;
            return true;
        }
        void __stdcall RenderTravel()
        {
            const auto view=Read();Prepare(view);Theme theme;
            Im::BeginChild("WalkWithMeTravel",{0,0});Im::SetWindowFontScale(.70F);Header(view,"");
            Label("TRAVEL",4);
            if(Rows("travel")){
                Im::TableNextColumn();Im::TextUnformatted("Default travel style");Im::TableNextColumn();Im::SetNextItemWidth(-1);
                int mode=static_cast<int>(draft.mode);if(Im::Combo("##mode",&mode,"Natural\0Lead\0Companion\0Rear\0Relax\0Vanilla\0")){draft.mode=profileModes[mode];dirty=true;}
                Slider("Spacing",draft.travel.spacing,.6F,3.0F,"%.2fx","Distance between travelling companions. Larger values spread them out; interiors and narrow paths still constrain space. Changes take effect immediately.");
                Im::TableNextColumn();Im::TextUnformatted("Adjust spacing");Im::TableNextColumn();
                if(Im::SmallButton("Tighten")){draft.travel.spacing=std::max(.6F,draft.travel.spacing-.2F);dirty=true;}
                Im::SameLine();if(Im::SmallButton("Spread out")){draft.travel.spacing=std::min(3.0F,draft.travel.spacing+.2F);dirty=true;}
                if(draft.mode==FormationMode::kDynamic)Slider("Straggler distance",draft.travel.naturalStragglerDistance,0,800,"%.0f units","Extra setback for one or two Natural-mode companions. Their mutual spacing stays normal. The choice stays stable while travelling; zero disables stragglers.");
                Slider("Catch-up response",draft.travel.catchUpSeconds,1,6,"%.1f s","Lower values close gaps more quickly.");
                Slider("Catch-up speed cap",draft.travel.maxSpeedScale,1,1.75F,"%.2fx","Normal catch-up limit. Distant companions use twice this value, then ease back to your pace.");
                Slider("Distant boost starts",draft.distantCatchupStart,300,std::min(2400.0F,draft.releaseDistance-100),"%.0f units","Beyond this player distance, catch-up uses twice your selected speed cap.");
                Slider("Normal pace within",draft.distantCatchupEnd,150,draft.distantCatchupStart-100,"%.0f units","The boost ends inside this distance. Separate thresholds prevent repeated speed switching.");
                Toggle("Teleport distant companions",draft.teleportCatchup,"Bring traveling companions back after two seconds far away. Uses clear ground behind you; waits during combat, conversations, scripted scenes, wait orders and rest. Companions in other interiors or worldspaces keep their own travel AI.");
                Im::BeginDisabled(!draft.teleportCatchup);
                Slider("Teleport beyond",draft.teleportDistance,1500,15000,"%.0f units","Distance from you before teleport catch-up. Each companion has a 15-second cooldown.");
                Im::EndDisabled();
                Slider("Anticipation",draft.travel.lookAhead,.2F,1.5F,"%.2f s","How far ahead the party predicts your route.");
                Toggle("Avoid obstacles ahead",draft.forwardCollision,"Take short, bounded detours around rocks while traveling nearby in the wilderness. Towns, interiors and distant catch-up use normal pathfinding. If a local detour fails, keep the native travel route. Hand-holding uses its own collision checks.");
                Slider("Turn response delay",draft.travel.turnDelay,0,.6F,"%.2f s","Wait briefly before following a new direction, ignoring little zigzags and softening side steps. Real reversals respond sooner. Zero restores immediate steering. Does not affect Vanilla mode.");
                Slider("Companion individuality",draft.travel.individuality,0,1,"%.2fx","Each companion has their own reaction time, turn response and comfortable pace. They let a small gap grow, then catch up. Higher values make the party less synchronized; zero restores shared movement. Large gaps still recover promptly. Does not affect Vanilla or sandboxing.");

                bool mirror=draft.preferredSide<0;Toggle("Swap preferred side",mirror,"Swap left and right.");draft.preferredSide=mirror?-1:1;
                Toggle("Outdoors only",draft.disableIndoors,"Release formation control inside buildings.");Im::EndTable();
            }
            Label("HAND HOLDING (EXPERIMENTAL)",3);
            if(Rows("handHolding")){
                auto& hands=draft.handHolding;
                Toggle("Hold hands (experimental)",hands.enabled,"Work in progress: hands and wrists can still twist, and approach/turn animations may look awkward. Disabled by default. Choose one companion to hold hands in third-person Companion mode while walking, jogging or running. Sprinting, weapons, combat, jumping, swimming, scenes and rest release the grip.");
                Im::TableNextColumn();Im::TextUnformatted("Hand-holding companion");Im::TableNextColumn();Im::SetNextItemWidth(-1);
                std::string preview=hands.partner.empty()?"None":hands.partnerName.empty()?"Selected companion":hands.partnerName;
                const bool nearby=std::any_of(view.party.begin(),view.party.end(),[&](const auto& row){return !hands.partner.empty()&&row.handHoldKey==hands.partner;});
                if(!hands.partner.empty()&&!nearby)preview+=" (not nearby)";
                if(Im::BeginCombo("##handHoldPartner",preview.c_str())){
                    if(Im::Selectable("None",hands.partner.empty())){hands.partner.clear();hands.partnerName.clear();dirty=true;}
                    for(const auto& row:view.party){
                        Im::PushID(static_cast<int>(row.id));
                        const bool selectable=!row.excluded&&!row.handHoldKey.empty();
                        Im::BeginDisabled(!selectable);
                        if(Im::Selectable(row.name.c_str(),!hands.partner.empty()&&row.handHoldKey==hands.partner)){
                            hands.partner=row.handHoldKey;hands.partnerName=row.name;dirty=true;
                        }
                        Im::EndDisabled();
                        if(!selectable)Help(row.handHoldKey.empty()?"This temporary actor has no persistent reference to remember. Choose a placed companion.":"Include this companion on the Party page first.");
                        Im::PopID();
                    }
                    Im::EndCombo();
                }
                Help("Only this companion is eligible, even in a group. After the lead-in they seek your hand regardless of formation spacing. If unavailable, the system waits for them. Selection saves automatically; changing it restarts the lead-in.");
                Slider("Lead-in delay",hands.delay,.5F,10,"%.1f s","Time in eligible Companion mode before looking for the selected follower. Paused menus do not count. Releasing the grip restarts this delay.");
                Slider("Connect within",hands.connectDistance,60,110,"%.0f units","Maximum distance between the two actors to begin reaching. Their arms must also be able to reach naturally.");
                hands.releaseDistance=std::max(hands.releaseDistance,hands.connectDistance+10);
                Slider("Release beyond",hands.releaseDistance,hands.connectDistance+10,160,"%.0f units","Release when separated beyond this distance, or sooner if either arm would overreach. Reconnection waits through the lead-in again.");
                Im::EndTable();
            }
            Label("REST & SANDBOX",3);
            if(Rows("sandbox")){
                Toggle("Relax when stopped",draft.sandbox.automatic,"Begin Walk With Me sandbox AI after you stand still. Its packages take priority over NFF sandboxing.");
                Slider("Begin after",draft.travel.idleRelease,2,30,"%.0f s","Time standing still before automatic sandboxing. Travel resumes when you leave the resume area.");
                Slider("Nearby rest radius",draft.sandbox.startRadius,40,std::min(600.0F,draft.releaseDistance-200),"%.0f units","Automatic stops only. Around 180 units leaves room to move and find nearby activities; very small areas can leave companions standing idle.");
                draft.sandbox.maxRadius=std::max(draft.sandbox.maxRadius,draft.sandbox.startRadius);
                Slider("Free-roam radius",draft.sandbox.maxRadius,draft.sandbox.startRadius,std::min(1800.0F,draft.releaseDistance-200),"%.0f units","Activity area used immediately by a Relax order, or after the automatic nearby phase ends.");
                Slider("Indoor & town range",draft.sandbox.settledActivityRadius,180,std::min(1800.0F,draft.releaseDistance-200),"%.0f units","Use nearby seats and activity markers from the start in homes, inns, other safe interiors and towns. Capped by Free-roam radius. Wilderness and dungeons keep the nearby phase; temporary rest keeps its resume distance.");
                Slider("Activity height",draft.sandbox.activityHeight,64,1600,"%.0f units","How far above or below the fixed rest anchor to seek activities. Connected stairs or ramps are required; low values keep searches near the current floor. Does not change Skyrim's global sandbox settings.");
                Slider("Free roam after",draft.sandbox.fullSandboxAfter,0,180,"%.0f s","Automatic stops only. One transition to the larger radius; current activities finish naturally. A direct Relax order skips this wait.");
                Slider("Resume following beyond",draft.sandbox.resumeDistance,100,1000,"%.0f units","Temporary rest continues while you stay within this distance of where you stopped, including dialogue. Relax ignores player distance.");
                Slider("Idle recovery delay",draft.sandbox.idleRecoveryAfter,0,120,"%.0f s","After sustained inactivity, allow a short walk inside the rest area. Personality adjusts this delay; staggered by up to 15 seconds, one companion at a time. Zero disables recovery.");
                Toggle("Conversation gestures",draft.sandbox.social,"Optional silent gestures between two nearby companions during free roaming. No grouping or movement orders; native conversations remain available.");
                Toggle("Extra rest poses",draft.sandbox.extraPoses,"Optional scripted poses. Off by default: Skyrim chooses its normal furniture, idles and activities.");
                if(draft.sandbox.extraPoses)Toggle("Ground sitting",draft.sandbox.groundSitting,"Sit on suitable outdoor wilderness ground. Never used inside buildings or dungeons.");
                Toggle("Eating & drinking",draft.sandbox.meals,"Native meals plus occasional refreshments for idle companions in safe interiors and towns. Inns favor drinking; other places favor food. Does not require Extra rest poses. Disabled in caves and dungeons.");
                if(draft.sandbox.extraPoses)Toggle("Reading",draft.sandbox.reading,"Read during quiet rests in safe locations.");
                if(draft.sandbox.extraPoses)Toggle("Stretching",draft.sandbox.stretching,"Occasional brief stretches between longer rests.");
                Im::EndTable();
            }
            Label("PARTY LIFE",3);
            if(Rows("partyLife")){
                Toggle("Celebrate battle victories",draft.victoryCelebrations,"After defeating at least five enemies in one fight, participating companions briefly clap or cheer. Requires a clear end to combat; skips busy or injured companions and stops when danger returns.");
                Toggle("Give conversations space",draft.conversationAwareness,"Other idle companions step aside during player dialogue. The speaking NPC, furniture users and active scenes are untouched.");
                Toggle("Walk during follower banter",draft.walkingBanter,"Keep simple two-follower conversations moving. Partners try to trade positions with a nearby companion and walk beside each other. Scripted movement scenes and player dialogue retain control.");
                if(draft.conversationAwareness)Slider("Conversation space",draft.conversationClearance,80,300,"%.0f units","Clearance around you, the NPC and the space between you. Only reachable positions are used.");
                Toggle("Companion personalities",draft.personalities,"Stable automatic tendencies affect socializing, exploration and lookout preference. Override each companion on the Party page.");
                Toggle("Occasional lookout",draft.lookouts,"During longer wilderness or dungeon rests, one free companion watches briefly. Requires at least three companions so two can still socialize.");
                if(draft.lookouts)Slider("Lookout after",draft.lookoutAfter,30,180,"%.0f s","Minimum rest time before a lookout. Watches last 30-45 seconds, with 90-150 seconds between watches.");
                Im::EndTable();
            }
            Label("ORDER EMBLEM",0);
            if(Rows("hud")){
                Toggle("Show emblem",draft.showOrderHUD,"Shows the current order on the right side of the screen.");
                Toggle("Soft HUD backing",draft.hudPanel,"Subtle dark backing behind the order. Disable for bare icon and text.");
                Slider("Size",draft.hudScale,.55F,1.3F,"%.2fx","Scale the small order emblem.");
                Slider("Height",draft.hudVertical,.1F,.85F,"%.2f","Distance down the right edge.");Im::EndTable();
                hudPreviewAt=GetTickCount64();hudPreviewEnabled=draft.showOrderHUD;
                hudPreviewScale=draft.hudScale;hudPreviewHeight=draft.hudVertical;
                hudPreviewPanel=draft.hudPanel;
                Note("Changes take effect and save automatically.");
            }
            if(Im::CollapsingHeader("Troubleshooting")){
                if(Rows("debug")){Toggle("Eligibility log",draft.logDiagnostics,"Record why a companion is released.");Toggle("Movement log",draft.traceMovement,"Record movement samples once per second.");Im::EndTable();}
            }
            if(Im::SmallButton("Restore travel defaults")){draft.travel=SettingsData{}.travel;draft.sandbox=SettingsData{}.sandbox;draft.distantCatchupStart=900;draft.distantCatchupEnd=500;draft.teleportCatchup=true;draft.teleportDistance=4000;draft.forwardCollision=true;draft.preferredSide=1;draft.disableIndoors=false;dirty=true;}
            Footer();Im::EndChild();
        }
        void __stdcall RenderControls()
        {
            const auto view = Read(); Prepare(view); Theme theme;
            Im::BeginChild("WalkWithMeControls", { 0, 0 });
            Im::SetWindowFontScale(0.70F);
            Header(view, "Orders within reach. Bind only what you use.");
            Label("KEY BINDINGS",6);
            Note("Select a binding, then hold Shift, Ctrl or Alt and press a key. Modifiers can be combined; either side works. Esc cancels; Delete clears.");
            Note("Use the exact combination: G, Ctrl + G and Shift + G can each have their own action.");
            Space();
            if (Im::BeginTable("bindings", 3, Im::ImGuiTableFlags_SizingStretchProp)) {
                Im::TableSetupColumn("Action", Im::ImGuiTableColumnFlags_WidthStretch, 1.4F);
                Im::TableSetupColumn("Key", Im::ImGuiTableColumnFlags_WidthStretch, 1.0F);
                Im::TableSetupColumn("", Im::ImGuiTableColumnFlags_WidthFixed, E(3.5F));
                for (int i = 0; i < 7; ++i) {
                    Im::PushID(i); Im::TableNextRow(); Im::TableNextColumn();
                    Im::TextUnformatted(hotkeyBindings[i].label); Im::TableNextColumn();
                    const bool waiting = capturing.load() == i;
                    const auto chord = hotkeyBindings[i].Get(draft);
                    const auto name = waiting ? "Press a key or chord..." : Hotkeys::ModifierPrefix(chord.modifiers) + KeyName(chord.key);
                    if (Im::Button(name.c_str(), { -1, 0 })) {
                        if (waiting) { CancelCapture(); } else { StartCapture(i); }
                    }
                    Im::TableNextColumn();
                    if (Im::Button("Clear", { -1, 0 })) { hotkeyBindings[i].Set(draft, {}); dirty = true; CancelCapture(); }
                    Im::PopID();
                }
                Im::EndTable();
            }
            Label("PARTY ORDERS",0);
            if(Im::Combo("Gamepad wheel",&draft.gamepadBinding,"Unbound\0LB + Right-stick click\0LB + Y\0LB + D-pad up\0"))dirty=true;
            Help("Hold LB and press the chosen button to open. Right stick aims; A confirms; B cancels. Camera look is consumed only while the wheel is open.");
            if(Im::Checkbox("Command hand signal",&draft.commandGestures))dirty=true;
            Help("Includes original third-person gestures for Lead, Companion and Rear, with female variants. First person and other orders use installed First Person Interactions clips. Requires Open Animation Replacer and generated GP Offset Movement Animation behaviors. Skips busy channels and weapons drawn.");
            if(draft.commandGestures){
                if(Im::Checkbox("Glance toward followers",&draft.gestureAwareness))dirty=true;
                Help("Briefly turn your head toward the party during a signal. A stronger glance for followers behind you, a subtle turn for those beside you. Third person only.");
                if(Im::Checkbox("Point for Lead",&draft.pointingSignal))dirty=true;
                Help("Use the bundled left-hand point in third person. First person keeps the installed FPI forward reach; movement remains free.");
                if(Im::Checkbox("Invitation for Companion",&draft.companionSignal))dirty=true;
                Help("Use the bundled two-arm invitation in third person with upper-body blending. First person uses the installed FPI wave.");
            }

            if (Im::Button("Open party orders") && commandWindow) { SetWheelOpen(true); }
            Help("Commands pause in game menus. Avoid keys used by other mods or Skyrim quicksave / quickload.");
            Footer(); Im::EndChild();
        }

        void __stdcall RenderCommands()
        {
            if(!commandWindow||!commandWindow->IsOpen)return;
            const auto view=Read();Theme theme;
            static float elapsed=0,centerElapsed=0;
            static Wheel::Motion motion;
            static int focus=0,lastFocus=-1,pressed=-1;
            static Wheel::Stick stick;
            const auto display=Im::GetIO()->DisplaySize;
            const float w=std::min(680.0F,std::min(display.x*.8F,display.y*.70F));
            const float dt=std::min(Im::GetIO()->DeltaTime,.05F);
            Im::SetNextWindowPos({display.x*.5F,display.y*.5F},Im::ImGuiCond_Always,{.5F,.5F});
            Im::SetNextWindowSize({w,w*1.08F},Im::ImGuiCond_Always);
            bool open=true;
            Im::PushStyleVar(Im::ImGuiStyleVar_WindowBorderSize,0.0F);
            Im::PushStyleColor(Im::ImGuiCol_WindowBg,IM_COL32(0,0,0,0));
            if(Im::Begin("WalkWithMeOrders",&open,Im::ImGuiWindowFlags_NoTitleBar|Im::ImGuiWindowFlags_NoResize|Im::ImGuiWindowFlags_NoMove|Im::ImGuiWindowFlags_NoScrollbar|Im::ImGuiWindowFlags_NoSavedSettings|Im::ImGuiWindowFlags_NoNav)){
                if(Im::IsWindowAppearing()){elapsed=0;focus=std::clamp(static_cast<int>(view.mode),0,Wheel::count-1);lastFocus=-1;pressed=-1;stick={};padConfirm=false;padCancel=false;padStep=0;motion.Open(focus);}
                if(wheelCloseRequested.load())motion.Close();
                elapsed+=dt;centerElapsed+=dt;
                const auto origin=Im::GetWindowPos();auto* draw=Im::GetWindowDrawList();
                const V center{origin.x+w*.5F,origin.y+w*.48F};
                const float hitRadius=w*.40F;
                auto* backdrop=Im::GetBackgroundDrawList();
                const auto mouse=Im::GetIO()->MousePos;
                int over=Wheel::Mouse(mouse.x-center.x,mouse.y-center.y,hitRadius);
                Im::BeginDisabled(motion.closing);

                Im::SetCursorScreenPos({origin.x,origin.y+w*.04F});
                const bool clicked=Im::InvisibleButton("wheel-hit",{w,w*.87F});
                const bool activated=Im::IsItemActivated();
                if(!Im::IsItemHovered())over=-1;
                if(activated)pressed=over;
                int choice=clicked&&pressed>=0&&pressed==over?over:-1;
                if(!Im::IsItemActive())pressed=-1;
                const bool mouseMoved=std::abs(Im::GetIO()->MouseDelta.x)+std::abs(Im::GetIO()->MouseDelta.y)>.5F;
                int step=padStep.exchange(0);
                if(Im::IsKeyPressed(Im::ImGuiKey_RightArrow)||Im::IsKeyPressed(Im::ImGuiKey_DownArrow))++step;
                if(Im::IsKeyPressed(Im::ImGuiKey_LeftArrow)||Im::IsKeyPressed(Im::ImGuiKey_UpArrow))--step;
                if(step)focus=Wheel::clockwise[(Wheel::slots[focus]+(step>0?1:Wheel::count-1))%Wheel::count];
                if(padStickAt.load()&&GetTickCount64()-padStickAt.load()<350)focus=stick.Update(padX.load(),padY.load(),focus);
                else stick.engaged=false;
                if(over>=0&&(mouseMoved||activated))focus=over;
                if(focus!=lastFocus){lastFocus=focus;centerElapsed=0;}
                motion.Update(dt,focus);
                const float fade=motion.visibility;
                const float radius=hitRadius*motion.Scale();
                Draw::AddRectFilled(backdrop,{0,0},display,IM_COL32(7,12,16,165*fade),0,0);
                auto text=[&](const char* value,V at,float size,Im::ImU32 color,float width){
                    auto bounds=Im::CalcTextSize(value);size=std::min(size,width*Im::GetFontSize()/std::max(bounds.x,1.0F));
                    color=(color&0x00FFFFFFu)|(static_cast<Im::ImU32>(((color>>24)&255)*fade)<<24);
                    Draw::AddText(draw,Im::GetFont(),size,{at.x-bounds.x*size/Im::GetFontSize()*.5F,at.y},color,value);
                };
                text("W A L K   W I T H   M E",{center.x,origin.y+w*.005F},w*.025F,gold,w*.8F);
                text("P A R T Y   O R D E R S",{center.x,origin.y+w*.042F},w*.017F,muted,w*.8F);
                for(int layer=4;layer>0;--layer)Draw::AddCircleFilled(draw,center,radius+layer*w*.008F,IM_COL32(0,0,0,8*fade),128);
                Draw::AddCircle(draw,center,radius*1.023F,IM_COL32(170,153,115,45*fade),128,1);
                for(int mode=0;mode<Wheel::count;++mode){
                    const float a=Wheel::Angle(mode);
                    const float light=motion.highlight[mode];
                    const float reveal=Wheel::EaseOut((elapsed-Wheel::slots[mode]*.018F)/.25F);
                    const auto fill=IM_COL32(25+37*light,32+29*light,36+14*light,(230+15*light)*fade*reveal);
                    auto point=[&](float angle,float r){return V{center.x+std::cos(angle)*r,center.y+std::sin(angle)*r};};
                    const auto sliceCenter=point(a,w*.006F*light);
                    OrderVisuals::Sector(draw,sliceCenter,radius*(.975F+.025F*reveal),mode,fill);
                    Draw::PathArcTo(draw,sliceCenter,radius*.98F,a-Wheel::pi/6+.065F,a+Wheel::pi/6-.065F,24);
                    Draw::PathStroke(draw,IM_COL32(218,191,133,(25+145*light)*fade*reveal),0,1+light);
                    V at=point(a,radius*.755F);at.y-=w*.018F;
                    at.y-=w*.004F*light;
                    OrderVisuals::Icon(draw,at,w*(.088F+.008F*light),mode,elapsed,fade*reveal*(view.enabled?.68F+.32F*light:.4F));
                    text(profileNames[mode],{at.x,at.y+w*.062F},w*.025F,IM_COL32(155+67*light,156+63*light,149+58*light,255*reveal),w*.20F);
                    if(mode==static_cast<int>(view.mode))Draw::AddCircleFilled(draw,point(a,radius*.555F),w*.003F,IM_COL32(228,203,152,220*fade),16);
                }
                Draw::AddCircle(draw,center,radius*.445F+1,IM_COL32(20,28,29,45*fade),96,3);
                Draw::AddCircleFilled(draw,center,radius*.445F,IM_COL32(20,28,29,242*fade),96);
                Draw::AddCircle(draw,center,radius*.445F,IM_COL32(166,151,114,70*fade),64,1);
                Draw::PathArcTo(draw,center,radius*.462F,motion.angle-.30F,motion.angle+.30F,28);
                Draw::PathStroke(draw,IM_COL32(229,200,143,220*fade),0,2);
                constexpr const char* captions[]{"Find your own pace","Take the road ahead","Stay by my side","Watch our backs","Make yourselves at home","Return to follower AI"};
                for(int i=0;i<Wheel::count;++i){
                    const float weight=motion.centerWeight[i];if(weight<.005F)continue;
                    const float lift=w*.007F*(1-weight);
                    OrderVisuals::Icon(draw,{center.x,center.y-w*.060F+lift},w*.105F,i,i==focus?centerElapsed:3.0F,fade*weight);
                    {Inscription font;text(profileNames[i],{center.x,center.y+w*.018F+lift},w*.037F,IM_COL32(235,225,203,255*weight),w*.32F);}
                    text(captions[i],{center.x,center.y+w*.070F+lift},w*.020F,IM_COL32(164,168,165,255*weight),w*.33F);
                }
                if(padConfirm.exchange(false)||Im::IsKeyPressed(Im::ImGuiKey_Enter,false))choice=focus;
                for(int i=0;i<Wheel::count;++i)if(Im::IsKeyPressed(static_cast<Im::ImGuiKey>(Im::ImGuiKey_1+i),false))choice=i;
                const bool cancel=padCancel.exchange(false)||Im::IsKeyPressed(Im::ImGuiKey_Escape,false);
                if(cancel)open=false;
                else if(!motion.closing&&choice>=0&&view.inGame&&view.enabled){focus=choice;IssueStyle(OrderMode(choice));}
                const char* hints=padUsed.load()?"Right stick: aim    A: confirm    B: back":"Click / 1-6: choose    Enter: confirm    Esc: back";
                const std::string status=!view.inGame?"Available in game":!view.enabled?"Walk With Me is disabled":fmt::format("ACTIVE ORDER  /  {}",profileNames[std::clamp(static_cast<int>(view.mode),0,Wheel::count-1)]);
                text(status.c_str(),{center.x,origin.y+w*.92F},w*.019F,gold,w*.8F);
                text(hints,{center.x,origin.y+w*.957F},w*.018F,muted,w*.95F);
                Im::SetCursorScreenPos({center.x-w*.12F,origin.y+w*.985F});
                Im::PushStyleVar(Im::ImGuiStyleVar_Alpha,fade);
                if(Im::Button("Return",{w*.24F,w*.065F}))open=false;
                Im::PopStyleVar();
                Im::EndDisabled();
            }
            Im::End();Im::PopStyleColor();Im::PopStyleVar();
            if(!open)SetWheelOpen(false);
            if(motion.Finished()){commandWindow->IsOpen=false;wheelCloseRequested=false;QueueWheelBlur();}
        }
        void __stdcall RenderHUD()
        {
            if(capturing.load()>=0&&GetTickCount64()-captureStarted.load()>15000)CancelCapture();
            const auto view=Read();
            const bool preview=hudPreviewAt&&GetTickCount64()-hudPreviewAt<200;
            const bool show=preview?hudPreviewEnabled:view.settings.showOrderHUD;
            static HudNotice notice;static bool shown=false,wasPreview=false;static std::uint64_t seenOrder{};
            static HudNoticePresentation presentation;
            if(!view.inGame||!view.enabled||!show){shown=false;return;}
            if(!preview&&(!view.gameplay||MF::IsAnyBlockingWindowOpened()))return;
            const int mode=view.sandboxActive?4:std::clamp(static_cast<int>(view.mode),0,Wheel::count-1);
            const std::uint64_t key=(view.generation<<16)|(static_cast<std::uint64_t>(view.mode)<<8)|static_cast<std::uint64_t>(view.sandboxActive);
            const auto order=orderNotice.load();
            if(!preview){
                presentation.Update(view.generation,static_cast<int>(view.mode),view.sandboxActive,order!=seenOrder,!shown||wasPreview);
                notice.Update(key,Im::GetIO()->DeltaTime,!shown||wasPreview||order!=seenOrder);
            }
            seenOrder=order;shown=true;wasPreview=preview;
            const bool compact=!preview&&presentation.compact;
            const float alpha=preview?1:notice.Alpha();if(alpha<=0)return;
            const auto display=Im::GetIO()->DisplaySize;
            const float dpi=std::clamp(display.y/1080.0F,.65F,2.5F);
            const float scale=(preview?hudPreviewScale:view.settings.hudScale)*dpi;
            const float height=preview?hudPreviewHeight:view.settings.hudVertical;
            const float right=display.x-24*dpi+(preview||compact?0:notice.Slide()*dpi),y=display.y*height;
            auto* draw=Im::GetForegroundDrawList();
            if(compact){

                OrderVisuals::Icon(draw,{right-42*scale,y},14*scale,mode,5.0F,alpha,true);
                return;
            }
            if(preview?hudPreviewPanel:view.settings.hudPanel){
                Draw::AddRectFilledMultiColor(draw,{right-270*scale,y-44*scale},{right,y+44*scale},IM_COL32(20,27,29,0),IM_COL32(20,27,29,238*alpha),IM_COL32(20,27,29,238*alpha),IM_COL32(20,27,29,0));
                Draw::AddLine(draw,{right,y-44*scale},{right,y+44*scale},IM_COL32(198,173,125,255*alpha),2*scale);
            }
            OrderVisuals::Icon(draw,{right-42*scale,y},56*scale,mode,preview?5.0F:notice.elapsed,alpha);
            constexpr const char* titles[]{"Natural","Lead","Companion","Rear","At Ease","Vanilla"};
            constexpr const char* details[]{"Travelling together","Taking the lead","By your side","Watching your back","Resting here","Follower AI restored"};
            auto text=[&](const char* value,float yy,float size,Im::ImU32 color){auto bounds=Im::CalcTextSize(value);float x=right-86*scale-bounds.x*size/Im::GetFontSize();Draw::AddText(draw,Im::GetFont(),size,{x+1,yy+2},IM_COL32(0,0,0,210*alpha),value);Draw::AddText(draw,Im::GetFont(),size,{x,yy},color,value);};
            {Inscription font;text(titles[mode],y-18*scale,20*scale,IM_COL32(226,218,201,255*alpha));}
            text(details[mode],y+9*scale,12*scale,IM_COL32(166,172,169,255*alpha));
        }
        bool __stdcall OnInput(RE::InputEvent* event) { return HandleInput(event); }
        void __stdcall OnMenuEvent(MF::Model::EventType event)
        {
            QueueWheelBlur();
            if (event == MF::Model::EventType::kCloseMenu) { CancelCapture(); captured.store(-1); }
            if (event == MF::Model::EventType::kOpenMenu) { refresh.store(true); }
        }
    }

    bool HandleInput(RE::InputEvent* event)
    {
        if(event&&event->GetDevice()==RE::INPUT_DEVICE::kGamepad){
            const bool wheelOpen=commandWindow&&commandWindow->IsOpen;
            if(event->GetEventType()==RE::INPUT_EVENT_TYPE::kThumbstick){
                auto* stick=static_cast<RE::ThumbstickEvent*>(event);
                if(stick->IsRight()&&wheelOpen){padX=stick->xValue;padY=-stick->yValue;padStickAt=GetTickCount64();padUsed=true;return true;}
                return wheelOpen;
            }
            if(event->GetEventType()!=RE::INPUT_EVENT_TYPE::kButton)return wheelOpen;
            auto* button=event->AsButtonEvent();if(!button)return wheelOpen;
            const auto key=button->GetIDCode();
            const bool fresh=button->IsDown()&&(padHeld&key)==0;
            if(button->IsPressed())padHeld|=key;else padHeld&=~key;
            if(wheelOpen){
                padUsed=true;
                if(fresh){if(key==0x1000)padConfirm=true;else if(key==0x2000)padCancel=true;else if(key==1)--padStep;else if(key==2)++padStep;}
                return true;
            }
            const auto view=Read();const int binding=view.settings.gamepadBinding;
            constexpr std::array<std::uint32_t,4> triggers{0,0x80,0x8000,1};
            auto* ui=RE::UI::GetSingleton();
            if(fresh&&binding>0&&key==triggers[std::clamp(binding,0,3)]&&(padHeld&0x100)&&commandWindow&&view.inGame&&view.gameplay&&ui&&!ui->GameIsPaused()&&!ui->IsMenuOpen(RE::DialogueMenu::MENU_NAME)&&!ui->IsMenuOpen(RE::Console::MENU_NAME)&&!MF::IsAnyBlockingWindowOpened()){
                padConfirm=false;padCancel=false;padStep=0;padX=0;padY=0;padStickAt=0;padUsed=true;SetWheelOpen(true);return true;
            }
            return false;
        }
        if (!event || event->GetEventType() != RE::INPUT_EVENT_TYPE::kButton || event->GetDevice() != RE::INPUT_DEVICE::kKeyboard) { return false; }
        auto* button = event->AsButtonEvent();
        if (!button) { return false; }
        const auto key = static_cast<std::uint32_t>(button->GetIDCode());
        const auto modifiers = KeyboardModifiers();
        if (capturing.load() >= 0) {
            if (GetTickCount64() - captureStarted.load() > 15000) { CancelCapture(); return false; }
            const int chord = Hotkeys::Capture(key, modifiers, button->IsDown(), button->IsUp());
            if (chord >= 0) { int empty = -1; captured.compare_exchange_strong(empty, chord); }
            return true;  
        }
        if (!button->IsDown()) { return false; }
        padUsed=false;
        if (commandWindow && commandWindow->IsOpen) {
            if (key == 1 || hotkeyBindings[0].Get(Read().settings).Matches(key, modifiers)) { SetWheelOpen(false); return true; }
            return false;
        }
        if (installed && MF::IsAnyBlockingWindowOpened()) { return false; }
        auto* ui = RE::UI::GetSingleton();

        if (!ui || ui->GameIsPaused() || ui->IsMenuOpen(RE::Console::MENU_NAME) || ui->IsMenuOpen(RE::DialogueMenu::MENU_NAME) || ui->IsMenuOpen(RE::TweenMenu::MENU_NAME) || ui->IsMenuOpen(RE::InventoryMenu::MENU_NAME) || ui->IsMenuOpen(RE::MagicMenu::MENU_NAME) || ui->IsMenuOpen(RE::ContainerMenu::MENU_NAME) || ui->IsMenuOpen(RE::BarterMenu::MENU_NAME) || ui->IsMenuOpen(RE::MapMenu::MENU_NAME) || ui->IsMenuOpen(RE::JournalMenu::MENU_NAME) || ui->IsMenuOpen(RE::CraftingMenu::MENU_NAME) || ui->IsMenuOpen(RE::StatsMenu::MENU_NAME) || ui->IsMenuOpen(RE::FavoritesMenu::MENU_NAME) || ui->IsMenuOpen(RE::RaceSexMenu::MENU_NAME) || ui->IsMenuOpen(RE::BookMenu::MENU_NAME) || ui->IsMenuOpen(RE::SleepWaitMenu::MENU_NAME) || ui->IsMenuOpen(RE::MessageBoxMenu::MENU_NAME)) { return false; }
        const auto view = Read();
        if (!view.inGame) { return false; }
        int action = -1;
        for (int i = 0; i < 7; ++i) { if (hotkeyBindings[i].Get(view.settings).Matches(key, modifiers)) { action = i; break; } }
        if (action < 0) { return false; }
        if (action == 0) {
            if (commandWindow) { SetWheelOpen(true); }
            else { Engine::Notify("Walk With Me party menu requires SKSE Menu Framework 3"); }
        } else {
            Queue([action](auto& c) {
                switch (action) {
                case 1: {
                    auto value = c.Snapshot().settings; value.enabled = !c.IsEnabled();
                    if (c.ApplyPreferences(value)) { Engine::Notify(value.enabled ? "Walk With Me enabled" : "Walk With Me disabled"); }
                    else { Engine::Notify("Walk With Me could not save the enable setting"); }
                    break;
                }
                case 2: c.CycleMode(); break;
                case 3: c.GiveOrder(PartyOrder::kScout); break;
                case 4: c.GiveOrder(PartyOrder::kRear); break;
                case 5: c.GiveOrder(PartyOrder::kRoam); break;
                case 6: c.ReloadSettings(); break;
                }
                if(action>=2&&action<=5){++orderNotice;CommandGesture::Request(c.Snapshot().mode);}
            });
        }
        return true;
    }

    void Publish()
    {
        SyncWheelBlur();  
        const auto now = GetTickCount64();
        if (!refresh.exchange(false) && now < nextPublish) { return; }
        nextPublish = now + 250;
        Cache(FormationController::GetSingleton().Snapshot());
    }
    void Reset()
    {
        CommandGesture::Reset();padHeld=0;padX=0;padY=0;padStickAt=0;padConfirm=false;padCancel=false;padStep=0;
        if (commandWindow) { commandWindow->IsOpen = false; }wheelCloseRequested=false;
        SyncWheelBlur();
        CancelCapture(); captured.store(-1); refresh.store(true);
        std::lock_guard lock(viewMutex); cached.inGame = false; cached.gameplay = false; cached.party.clear();
    }
    bool IsInstalled() { return installed.load(); }
    void Register()
    {
        Cache(FormationController::GetSingleton().Snapshot());
        if (!GetModuleHandleW(L"SKSEMenuFramework.dll") || MF::GetMenuFrameworkVersion() < 3.0F) {
            logger::warn("[Menu] SKSE Menu Framework 3 not found; INI and keyboard controls remain available"); return;
        }
        MF::SetSection("Walk With Me");
        MF::AddSectionItem("Party", RenderParty);
        MF::AddSectionItem("Travel", RenderTravel);
        MF::AddSectionItem("Controls", RenderControls);
        commandWindow = MF::AddWindow(RenderCommands, true);
        inputRegistration.reset(MF::AddInputEvent(OnInput));
        hudRegistration.reset(MF::AddHudElement(RenderHUD));
        eventRegistration.reset(MF::AddEvent(OnMenuEvent, 0));
        installed.store(true);
        logger::info("[Menu] Party, Travel, Controls, command window and HUD registered (framework {})", MF::GetMenuFrameworkVersion());
    }
}
