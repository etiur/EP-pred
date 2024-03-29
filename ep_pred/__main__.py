import argparse
import glob
import os
from prediction.predict import vote_and_filter
from extract.feature_extraction import extract_and_filter
from pathlib import Path
from subprocess import call
import shlex
from os.path import dirname, basename, abspath
from Bio import SeqIO
from Bio.SeqIO import FastaIO


def arg_parse():
    parser = argparse.ArgumentParser(description="extract features using possum and ifeatures")
    parser.add_argument("-i", "--fasta_file", help="The fasta file path", required=False)
    parser.add_argument("-p", "--pssm_dir", help="The pssm files directory's path", required=False,
                        default="pssm")
    parser.add_argument("-f", "--fasta_dir", required=False, help="The directory for the fasta files",
                        default="fasta_files")
    parser.add_argument("-id", "--ifeature_dir", required=False, help="Path to the iFeature programme folder",
                        default="/gpfs/projects/bsc72/ruite/enzyminer/iFeature")
    parser.add_argument("-Po", "--possum_dir", required=False, help="A path to the possum programme",
                        default="/gpfs/projects/bsc72/ruite/enzyminer/POSSUM_Toolkit/")
    parser.add_argument("-io", "--ifeature_out", required=False, help="The directory where the ifeature features are",
                        default="ifeature_features")
    parser.add_argument("-po", "--possum_out", required=False, help="The directory for the possum extractions",
                        default="possum_features")
    parser.add_argument("-fo", "--filtered_out", required=False, help="The directory for the filtered features",
                        default="filtered_features")
    parser.add_argument("-di", "--dbinp", required=False, help="The path to the fasta files to create the database")
    parser.add_argument("-do", "--dbout", required=False, help="The path and name of the created database",
                        default="/gpfs/projects/bsc72/ruite/enzyminer/database/uniref50")
    parser.add_argument("-n", "--num_thread", required=False, default=100, type=int,
                        help="The number of threads to use for the generation of pssm profiles and feature extraction")
    parser.add_argument("-rs", "--res_dir", required=False,
                        default="results", help="The name for the folder where to store the prediction results")
    parser.add_argument("-nss", "--number_similar_samples", required=False, default=1, type=int,
                        help="The number of similar training samples to filter the predictions")
    parser.add_argument("-re", "--restart", required=False, choices=("feature", "predict"),
                        help="From which part of the process to restart with")
    parser.add_argument("-on", "--filter_only", required=False, help="true if you already have the features",
                        action="store_true")
    parser.add_argument("-lg", "--long", required=False, help="true when restarting from the long commands",
                        action="store_true")
    parser.add_argument("-r", "--run", required=False, choices=("possum", "ifeature", "both"), default="both",
                        help="run possum or ifeature extraction")
    parser.add_argument("-st", "--start", required=False, type=int, help="The starting number", default=1)
    parser.add_argument("-en", "--end", required=False, type=int, help="The ending number, not included")
    parser.add_argument("-sp", "--sbatch_path", required=False,
                        help="The folder to keep the run files for generating pssm", default="run_files")
    parser.add_argument("-v", "--value", required=False, default=1, type=float, choices=(1, 0.8, 0.5),
                        help="The voting threshold to be considered positive")
    parser.add_argument("-iter", "--iterations", required=False, default=3, type=int, help="The number of iterations "
                                                                                         "in PSIBlast")
    args = parser.parse_args()

    return [args.fasta_file, args.pssm_dir, args.fasta_dir, args.ifeature_dir, args.possum_dir, args.ifeature_out,
            args.possum_out, args.filtered_out, args.dbinp, args.dbout, args.num_thread, args.number_similar_samples,
            args.res_dir, args.restart, args.filter_only, args.long, args.run, args.start,
            args.end, args.sbatch_path, args.value, args.iterations]


class WriteSh:
    def __init__(self, fasta=None, fasta_dir="fasta_files", pssm_dir="pssm", num_threads=100, dbinp=None,
                 dbout="/gpfs/projects/bsc72/ruite/enzyminer/database/uniref50", run_path="run_files",
                 possum_dir="/gpfs/projects/bsc72/ruite/enzyminer/POSSUM_Toolkit/",
                 iterations=3):
        """
        Initialize the ExtractPssm class

        Parameters
        ___________
        fasta: str, optional
            The file to be analysed
        num_threads: int, optional
         The number of threads to use for the generation of pssm profiles
        fasta_dir: str, optional
            The directory of the fasta files
        pssm_dir: str, optional
            The directory for the output pssm files
        dbinp: str, optional
            The path to the protein database
        dbout: str, optional
            The name of the created databse database
        """
        self.fasta_file = fasta
        self.fasta_dir = fasta_dir
        self.pssm = pssm_dir
        self.dbinp = dbinp
        self.dbout = dbout
        self.num_thread = num_threads
        self.possum = possum_dir
        self.run_path = run_path
        self.iter = iterations
        self.base = Path(fasta).parent

    def write(self, num):
        if type(num) == str:
            nums = "all"
        else:
            nums = num
        if not os.path.exists(self.run_path):
            os.makedirs(self.run_path)
        with open(f"{self.run_path}/pssm_{nums}.sh", "w") as sh:
            lines = ["#!/bin/bash\n", f"#SBATCH -J pssm_{nums}\n", f"#SBATCH --output=pssm_{nums}.out\n",
                     f"#SBATCH --error=pssm_{nums}.err\n", f"#SBATCH --ntasks={self.num_thread}\n\n",
                     "module purge && module load gcc/7.2.0 blast/2.11.0 impi/2018.1 mkl/2018.1 python/3.7.4 perl\n",
                     'echo "Start at $(date)"\n', 'echo "-------------------------"\n']
            argument_list = []
            arguments = f"-f {self.fasta_dir} -p {self.pssm} -n {self.num_thread} "
            argument_list.append(arguments)
            if self.iter != 3:
                argument_list.append(f"-iter {self.iter} ")
            if self.fasta_file:
                argument_list.append(f"-i {self.fasta_file} ")
            if type(num) == int:
                argument_list.append(f"-num {num} ")
            if self.dbout != "/gpfs/projects/bsc72/ruite/enzyminer/database/uniref50":
                argument_list.append(f"-do {self.dbout} ")
            if self.dbinp:
                argument_list.append(f"-di {self.dbinp} ")
            all_arguments = "".join(argument_list)
            python = f"python /gpfs/projects/bsc72/ruite/enzyminer/extract/generate_pssm.py {all_arguments}\n"
            lines.append(python)
            lines.append('echo "End at $(date)"\n')
            sh.writelines(lines)

        return f"{self.run_path}/pssm_{nums}.sh"

    def write_all(self, start=1, end=None):
        """
        Parameters
        ----------
        start: int, optional
            The starting number, leave it to 1
        end: int, optional
            The ending number, not included
        """
        if start and end:
            for num in range(start, end):
                pssm = self.write(num)
                os.system(f"sbatch {pssm}")
        else:
            num = "*"
            pssm = self.write(num)
            os.system(f"sbatch {pssm}")

    def clean_fasta(self):
        """
        Clean the fasta file
        """
        illegal = f"perl {self.possum}/utils/removeIllegalSequences.pl -i {self.fasta_file} -o {self.base}/no_illegal.fasta"
        short = f"perl {self.possum}/utils/removeShortSequences.pl -i {self.base}/no_illegal.fasta -o {self.base}/no_short.fasta -n 100"
        call(shlex.split(illegal), close_fds=False)
        call(shlex.split(short), close_fds=False)

    def separate_single(self):
        """
        A function that separates the fasta files into individual files

        Returns
        _______
        file: iterator
            An iterator that stores the single-record fasta files
        """
        with open(f"{self.base}/no_short.fasta") as inp:
            record = SeqIO.parse(inp, "fasta")
            count = 1
            # write the record into new fasta files
            for seq in record:
                with open(f"{self.fasta_dir}/seq_{count}.fsa", "w") as split:
                    fasta_out = FastaIO.FastaWriter(split, wrap=None)
                    fasta_out.write_record(seq)
                count += 1

    def remove_sequences_from_input(self):
        """
        A function that removes the fasta sequences that psiblast cannot generate pssm files from,
        from the input fasta file. If inside the remove dir there are fasta files them you have to use this function.
        """
        # I search for fasta files that doesn't have pssm files
        fasta_file = list(
            map(lambda x: basename(x.replace(".fsa", "")), glob.glob(f"{abspath('removed_dir')}/seq_*.fsa")))
        difference = sorted(fasta_file, key=lambda x: int(x.split("_")[1]), reverse=True)
        if len(difference) > 0 and not os.path.exists(f"{self.base}/no_short_before_pssm.fasta"):
            with open(f"{self.base}/no_short.fasta") as inp:
                record = SeqIO.parse(inp, "fasta")
                record_list = list(record)
                # I eliminate the sequences from the input fasta file and move the single fasta sequences
                # to another folder
                for files in difference:
                    num = int(files.split("_")[1]) - 1
                    del record_list[num]
                    # I rename the input fasta file so to create a new input fasta file with the correct sequences
                os.rename(f"{self.base}/no_short.fasta", f"{self.base}/no_short_before_pssm.fasta")
                with open(f"{self.base}/no_short.fasta", "w") as out:
                    fasta_out = FastaIO.FastaWriter(out, wrap=None)
                    fasta_out.write_file(record_list)


def main():
    fasta_file, pssm_dir, fasta_dir, ifeature_dir, possum_dir, ifeature_out, possum_out, filtered_out, dbinp, dbout, \
    num_thread, min_num, res_dir, restart, filter_only, long, run, start, end, sbatch_path, \
    value, iterations = arg_parse()

    sh = WriteSh(fasta_file, fasta_dir, pssm_dir, num_thread, dbinp, dbout, sbatch_path, possum_dir, iterations)
    if not restart:
        Path(fasta_dir).mkdir(exist_ok=True, parents=True)
        if not next(os.scandir(f"{fasta_dir}"), False):
            sh.clean_fasta()
            sh.separate_single()
        files = glob.glob(f"{sbatch_path}/pssm_*.sh")
        if not files:
            sh.write_all(start, end)
        else:
            for file in files:
                os.system(f"sbatch {file}")
    if restart == "feature":
        sh.remove_sequences_from_input()
        extract_and_filter(fasta_file, pssm_dir, fasta_dir, ifeature_out, possum_dir, ifeature_dir, possum_out,
                           filtered_out, filter_only, long, num_thread, run)
        restart = "predict"
    if restart == "predict":
        vote_and_filter(filtered_out, fasta_file, min_num, res_dir, value)

    
if __name__ == "__main__":
    # Run this if this file is executed from command line but not if is imported as API
    main()