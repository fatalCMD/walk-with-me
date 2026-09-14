#pragma once

inline void SetupLog(std::string_view a_pluginName)
{
    auto path = logger::log_directory();
    if (!path) {
        SKSE::stl::report_and_fail("Walk With Me could not locate the SKSE log directory."sv);
    }

    *path /= fmt::format("{}.log", a_pluginName);
    auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);
    auto log = std::make_shared<spdlog::logger>("global log", std::move(sink));
    log->set_level(spdlog::level::info);
    log->flush_on(spdlog::level::info);
    spdlog::set_default_logger(std::move(log));
    spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%l] %v");
}
