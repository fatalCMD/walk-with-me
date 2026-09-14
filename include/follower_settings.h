#pragma once
#include <SimpleIni.h>

namespace Wayfarer
{
    inline bool MigrateFollowerSettings(CSimpleIniA& ini)
    {
        if (ini.GetLongValue("General", "iEnrollmentVersion", 0) >= 1) {
            return false;
        }
        ini.SetBoolValue("General", "bAutoDiscover", true);
        ini.SetLongValue("General", "iEnrollmentVersion", 1);
        return true;
    }
}
