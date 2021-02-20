
version 1.0

task Bamtools_index
{
  input {
    Int cpu = 4
    Int mem = 4
    String sample_id
    String  main
    String group_name
    String sample_id
    String    input_bam
     String   read1
      String  read2
     String   quality
  }

  command {
    ${main} ${input_bam} ${group_name} ${sample_id} ${read1} ${read2} ${quality}
  }

  runtime {
    backend: "SGE"
    cpu: "${cpu}"
    memory: "${mem} GB"
  }

  output {
    File result = "./stdout"
  }
}
