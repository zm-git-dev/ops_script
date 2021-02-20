version 1.0

task PrepareInput
{
  input {
    String tools_main
    Array[Array[String]] data
    String param_json
    String? adapter3
    String? adapter5
    String? parameter
  }

  command {
    python3 ${tools_main} prepare ${write_tsv(data)} ${param_json} ${"--adapter3 " + adapter3} ${"--adapter5 " + adapter5} ${parameter} && sleep 20
  }

  output {
    Map[String, String] param = read_json(param_json)
  }
}

task ResultArchive
{
  input {
    String tools_main
    Array[Array[String]] data
    String param_json = "param.json"
    String result_dir
    String? parameter
  }

  command {
    python3 ${tools_main} archive ${write_tsv(data)} ${param_json} ${parameter} --result-dir  ${result_dir} && sleep 20
  }

  output {
#    Map[String, String] param = read_json(param_json)
  }
}


task GetQcValues
{
  input {
    String tools_main
    Array[Array[String]] data
    String param_json = "param.json"
    String result_dir
    String? parameter
  }

  command {
    python3 ${tools_main} get-qc-values ${write_tsv(data)} ${param_json} ${parameter} --result-dir  ${result_dir} && sleep 20
  }

  output {
    Map[String, String] qc_values = read_json(param_json)["qc_values"]
    Map[String, String] standards = read_json(param_json)["standards"]
  }
}

task GetManyQcValues
{
  input {
    String tools_main
    Array[Array[String]] data
    String param_json = "param.json"
    Map[String, String] result_dir
    String? parameter
  }

  command {
    python3 ${tools_main} get-qc-values ${write_tsv(data)} ${param_json} ${parameter} --result-dir  ${write_map(result_dir)} && sleep 20
  }

  output {
    Map[String, String] qc_values = read_json(param_json)["qc_values"]
    Map[String, String] standards = read_json(param_json)["standards"]
  }
}

task UpdateFlow
{
  input {
    String tools_main
    Array[Array[String]] data
    String param_json = "param.json"
    String result_dir
    String? parameter
  }

  command {
    python3 ${tools_main} update-flow ${write_tsv(data)} ${param_json} ${parameter} --result-dir  ${result_dir} && sleep 20
  }

  runtime {
    backend: "Local"
  }

  output {
    Map[String, String] param = read_json(param_json)
  }
}