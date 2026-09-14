"""Guard integration boundaries that pure behavior tests cannot exercise."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'src/formation_controller.cpp').read_text()
awareness=s.split('void FormationController::UpdateConversationAwareness(',1)[1].split('void FormationController::UpdateLookout(',1)[0]
for forbidden in ('ForceRefTo','CreateReferenceAtLocation','EnsureQuest(', 'ReleaseAll(', 'SetSandboxFlag(', 'SetPoseFlag('):
 assert forbidden not in awareness, f'dialogue awareness must not call {forbidden}'
assert 'id==speaker->GetFormID()' in awareness
assert 'destinationAlias->GetReference()!=target.get()' in awareness
assert 'followerAlias->GetReference()!=actor.get()' in awareness
assert 'current!=travel && current!=rest' in awareness
assert 'actor->GetCurrentScene()' in awareness and 'IsSpeaking(*actor)' in awareness
assert 'GetOccupiedFurniture' in awareness and 'IsInCombat' in awareness
assert 'awarenessTime>=15' in awareness
assert 'EndConversationAwareness();' in s
script=(r/'package/Scripts/Source/WayfarerQuestScript.psc').read_text()
assert script.index('If Wayfarer.ShouldSuspendForDialogue()')<script.index('strollAlias.ForceRefTo')
assert 'If Wayfarer.GetGatherMarker(slot) == strollTarget\n                    If StopSyncForDialogue()' in script
settings=(r/'src/config.cpp').read_text()
for key in ('bConversationAwareness','bPersonalities','bLookouts','fConversationClearance','fLookoutAfter'):
 assert settings.count('"'+key+'"')==2, f'{key} must load and save'
assert 'GetAllKeys("Personalities"' in settings and 'SetLongValue("Personalities"' in settings
print('Party life integration checked: protected dialogue participants, ready aliases only, owned packages only, activity guards, bounded walks and settings persistence.')
