import subprocess


def get_nodelist(job_step):
    """
    Blocks until job step is assigned a node
    """
    while True:
        cmd = ["sacct", "-n", "--parsable2", "-j", job_step, "-o", "NodeList"]
        output = subprocess.check_output(cmd)
        if len(output) > 0 and output != b"None assigned\n":
            return output.decode().strip()
