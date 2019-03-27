from strictyaml import (
    Map,
    Regex,
    Seq,
    Str,
    Int,
    Optional,
    Seq,
    MapPattern,
    Enum,
    Bool,
    Any,
)

limits_schema = Map(
    {
        "time": Int(),
        Optional("memory", default=8192): Int(),
        Optional("output"): Int(),
        Optional("cores"): Str(),
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
            {"run": Seq(plugin_schema), Optional("compile"): Seq(plugin_schema)}
        ),
        "observers": Seq(plugin_schema),
        "tasks": MapPattern(Str(), MapPattern(Str(), Any())),
        "tools": MapPattern(
            Str(), Map({"module": module_schema, "parameters": Seq(Str())})
        ),
        "parameters": MapPattern(Str(), MapPattern(Str(), Any())),
    }
)
