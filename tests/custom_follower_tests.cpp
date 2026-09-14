#include "custom_followers.h"
#include "follower_settings.h"
#include <iostream>
#include <limits>

int main()
{
    using namespace Wayfarer;
    int failures = 0;
    auto check = [&](bool ok, const char* reason) { if (!ok) { ++failures; std::cerr << reason << '\n'; } };
    check(KnownCustomFollower("018auri.esp", 0xD63), "Auri is custom even while in vanilla follower faction");
    check(KnownCustomFollower("dawnguard.esm", 0x2B6C), "Serana uses her own framework");
    check(!KnownCustomFollower("dawnguard.esm", 0x336A), "Other Dawnguard NPCs are not Serana");
    check(!KnownCustomFollower("skyrim.esm", 0x2B6C), "Base ID alone does not identify Serana");
    check(!UsesCustomFollowerAI("skyrim.esm", 0xB9982, true, true), "Vanilla hireling keeps ordinary discovery");
    check(UsesCustomFollowerAI("3dnpc.esp", 0x123, true, true), "Other modded followers also honor the custom toggle");
    check(!UsesCustomFollowerAI("3dnpc.esp", 0x123, false, true), "Mod origin alone does not recruit an actor");
    check(UsesCustomFollowerAI("skyrim.esm", 0x123, true, false), "Nonstandard teammate can be enforced without vanilla faction");
    check(HasCustomFollowState(true, 0), "Recruited custom teammate is discoverable");
    check(!HasCustomFollowState(false, 0), "Unrecruited follower is not acquired");
    check(!HasCustomFollowState(true, -1), "Dismissed Inigo stays a teammate but must not be reacquired");
    check(HasCustomFollowState(true, 1) && HasCustomFollowState(true, 2), "Waiting and resting companions remain in the roster");
    check(!HasCustomFollowState(true, std::numeric_limits<float>::quiet_NaN()), "Unknown follow state is rejected");
    std::unordered_set<std::string> old;
    for (auto name : legacyCustomExclusions) { old.emplace(name); }
    check(IsLegacyCustomBlocklist(old), "Exact shipped defaults can migrate");
    old.erase("018auri.esp");
    check(!IsLegacyCustomBlocklist(old), "User-edited blocklist must survive");
    old.emplace("018auri.esp"); old.emplace("myfollower.esp");
    check(!IsLegacyCustomBlocklist(old), "Additional user exclusions must survive");
    check(!IsLegacyCustomBlocklist({}), "Empty defaults need no migration");
    CSimpleIniA ini;
    ini.LoadData("[General]\nbAutoDiscover=false\n[Compatibility]\nbEnforceCustomFollowers=false\nsExcludedPlugins=myfollower.esp\n");
    check(MigrateFollowerSettings(ini) && ini.GetBoolValue("General", "bAutoDiscover"), "Old manual default upgrades to automatic enrollment");
    check(!ini.GetBoolValue("Compatibility", "bEnforceCustomFollowers"), "Upgrade preserves custom enforcement preference");
    check(std::string(ini.GetValue("Compatibility", "sExcludedPlugins")) == "myfollower.esp", "Upgrade preserves exclusions");
    ini.SetBoolValue("General", "bAutoDiscover", false);
    std::string saved;
    ini.Save(saved);
    CSimpleIniA reloaded;
    reloaded.LoadData(saved.c_str());
    check(!MigrateFollowerSettings(reloaded) && !reloaded.GetBoolValue("General", "bAutoDiscover"), "Disabling automatic enrollment survives reload");
    CSimpleIniA fresh;
    check(MigrateFollowerSettings(fresh) && fresh.GetBoolValue("General", "bAutoDiscover"), "Missing enrollment settings enable discovery");
    return failures ? 1 : 0;
}
