
version 1.0
import "Sentieon.wdl"


workflow sentieon {
  input {
    String quality = "Q20"
    Int cpu = 3
    String mem = "100G"
  }

  String param_json = "param.json"

    call Sentieon.Bamtools_index {
        input:
        main = "echo",
        group_name = ${sample.metadata.group_name},
        sample_id = SampleID,
        input_bam = ${sample.metadata.files.input_bam},
        read1 = ${sample.metadata.files.read1},
        read2 = ${sample.metadata.files.read2},
        quality = quality
    }


  output {
    File result = Bamtools_index.result

  }

  parameter_meta {}
}
