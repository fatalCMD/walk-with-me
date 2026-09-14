#pragma once
#include <cstdint>
#include "formation_math.h"
namespace Wayfarer::CommandGesture {
void Request(FormationMode mode);  
void Update(float dt);  
void Reset();
bool Available();
std::uint32_t SavedOwnership();  
void RestoreSelector(std::uint32_t saved);
}
