from strictyaml import Any, Enum, Int, Map, MapPattern, Optional, Regex, Seq, Str

limits_schema = Map(
    {
        "time": Int(),
        Optional("memory", default=8192): Int(),
        Optional("output"): Int(),
        Optional("cores"): Int(),
    }
)

module_schema = Regex(r"\.?\w+(\.\w+)*")

plugin_schema = Map(
    {"module": module_schema, Optional("config"): MapPattern(Str(), Any())}
)

task_sources = Enum(["local", "url"])

schema = Map(
    {
        "title": Str(),
        Optional("description"): Str(),
        "limits": limits_schema,
        "steps": Map(
            {"run": Seq(plugin_schema), Optional("analysis"): Seq(plugin_schema)}
        ),
        "observers": Seq(plugin_schema),
        "tasks": MapPattern(Str(), MapPattern(Str(), Any())),
        "tools": MapPattern(
            Str(),
            Map(
                {
                    "module": module_schema,
                    Optional("parameters"): MapPattern(Str(), MapPattern(Str(), Any())),
                }
            ),
        ),
    }
)
