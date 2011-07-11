from subprocess import call
from rapl.parameters import Parameters
from rapl.paths import Paths
from libs.sam import SamBuilder, SamParser

class ReadMapper(object):

    def __init__(self):
        self.paths = Paths()
        self.parameters = Parameters()
    
    def build_segmehl_index(self):
        """Create the segemehl index based on the genome files."""
        call("%s -x %s -d %s" % (
                self.paths.segemehl_bin, self.paths.segemehl_index(),
                " ".join(self.paths.genome_file_paths())), 
             shell=True)

    def run_mapping_with_raw_reads(self):
        """Run the mapping of the raw reads using segemehl"""
        for read_file in self.paths.read_files:
            self._run_segemehl_search(
                self.paths.read_file(read_file),
                self.paths.raw_read_mapping_output(read_file),
                self.paths.unmapped_raw_read_file(read_file))

    def _run_segemehl_search(self, read_file_path, output_file_path, 
                             unmapped_read_file_path):
        """Call segemehl to do a mapping.

        Arguments:
        - `read_file_path`: the file path of the read fasta file
        - `output_file_path`: the path of the Segemehl output
        - `unmapped_read_file_path`: the path of the fasta of 
                                     unmapped reads

        """
        # Can only be used with the developmental version of segemehl
        call("%s -K -E %s -H %s -A %s -t %s -i %s -d %s -q %s -o %s -u %s" % (
                self.paths.segemehl_bin,
                self.parameters.segemehl_max_e_value,
                self.parameters.segemehl_hit_strategy,
                self.parameters.segemehl_accuracy,
                self.parameters.segemehl_number_of_threads,
                self.paths.segemehl_index(),
                " ".join(self.paths.genome_file_paths()),
                read_file_path,
                output_file_path,
                unmapped_read_file_path),
             shell=True)

    def clip_unmapped_reads(self):
        """Clip reads unmapped in the first segemehl run."""
        for read_file in self.paths.read_files:
            self._clip_reads(self.paths.unmapped_raw_read_file(read_file))

    def _clip_reads(self, unmapped_raw_read_file_path):
        """Remove the poly-A tail of reads in a file.

        Arguments:
        - `unmapped_raw_read_file_path`: path of the fasta file that
                                         contains unmapped reads

        """
        call("%s %s/poly_a_clipper.py %s" % (self.paths.python_bin,
                self.paths.bin_folder, unmapped_raw_read_file_path), shell=True)

    def filter_clipped_reads_by_size(self):
        """Filter clipped reads sequence length.

        For each read file two output files are generated. One
        contains reads with a size equal or higher than the given
        cut-off. One for the smaller ones.

        """
        for read_file in self.paths.read_files:
            self._filter_reads_by_size(self.paths.unmapped_read_clipped(read_file))

    def _filter_reads_by_size(self, read_file_path):
        """Filter reads by sequence length.

        Arguments:
        - `read_file_path`: path of the fasta file that will be split.

        """
        call("%s %s/filter_fasta_entries_by_size.py %s %s" % (
                self.paths.python_bin, self.paths.bin_folder, read_file_path, 
                self.parameters.min_seq_length), shell=True)

    def run_mapping_with_clipped_reads(self):
        """Run the mapping with clipped and size filtered reads."""
        for read_file in self.paths.read_files:
            self._run_segemehl_search(
                self.paths.unmapped_clipped_size_filtered_read(read_file), 
                self.paths.clipped_reads_mapping_output(read_file),
                self.paths.unmapped_reads_of_clipped_reads_file(read_file))
            print(self.paths.unmapped_reads_of_clipped_reads_file(read_file))

    def combine_mappings(self):
        """Combine the results of both segemehl mappings for all libraries."""
        for read_file in self.paths.read_files:
            self._combine_mappings(read_file)

    def _combine_mappings(self, read_file):
        """Combine the results of both segemehl mappings.

        Arguments:
        - `read_file`: the name of the read file that was used to generate
                       the Segemehl mappings.

        """
        comined_mappings_fh = open(self.paths.combined_mapping_file(read_file), "w")
        comined_mappings_fh.write(open(self.paths.raw_read_mapping_output(read_file)).read())
        comined_mappings_fh.write(open(self.paths.clipped_reads_mapping_output(read_file)).read())
        comined_mappings_fh.close()

    def filter_combined_mappings_by_a_content(self):
        """Filter Segemehl mapping file entries by amount of A content.

        This removes sequences that exceed a certain amount of A that
        might be introduced during the sample preparion process.

        """
        for read_file in  self.paths.read_files:
            self._filter_combined_mappings_by_a_content(read_file)
    
    def _filter_combined_mappings_by_a_content(self, mapping_file):
        """Filter Segemehl mapping file entries by A-content.

        Two files are produced. One that contains reads that have an
        A-content higher than the cut-off value, one that contains the
        reads that have A-content equal or lower than the cut-off
        value.

        Arguments:
        - `mapping_file`: the input mapping file 

        """
        call("%s %s/filter_sam_by_nucleotide_percentage.py %s A %s " % (
            self.paths.python_bin, self.paths.bin_folder, 
            self.paths.combined_mapping_file(mapping_file), self.parameters.max_a_content), 
             shell=True)

    # # TODO: Obsolete - remove
    # def split_mappings_by_genome_files(self):
    #     """Split the Segemehl result entries by genome file."""
    #     headers_of_genome_files = self.helper.get_headers_of_genome_files()
    #     for read_file in  self.paths.read_files:
    #         self._split_mapping_by_genome_files(
    #             read_file, headers_of_genome_files)

    # # TODO: Obsolete - remove
    # def _split_mapping_by_genome_files(self, read_file, headers_of_genome_files):
    #     """Split the Segemehl results by the target genome files.

    #     Arguments:
    #     - `read_file,`: the read file that was used to generate the combined
    #                     Segemehl mapping file
    #     - `headers_of_genome_files`: A dictionary that contains the headers
    #                                  of the genome files as keys and the
    #                                  name of their files as values.

    #     """
    #     sam_parser = SamParser()
    #     sam_builder = SamBuilder()        
    #     file_handles = {}
    #     # Open an output file for each genome file. Needed as some
    #     # genome files don't have any mapping and so their mapping
    #     # file would not be created otherwise and be missing later.
    #     for genome_file in self.paths.genome_files:
    #         output_file = self.paths.combined_mapping_file_a_filtered_split(
    #             read_file, genome_file)
    #         file_handles["%s-%s" % (read_file, genome_file)] = open(
    #             output_file, "w")
    #     for entry in sam_parser.entries(
    #         self.paths.combined_mapping_file_a_filtered(read_file)):
    #         genome_file = headers_of_genome_files[entry['reference']]
    #         file_handles["%s-%s" % (read_file, genome_file)].write(
    #             sam_builder.entry_to_line(entry))
    #     for output_file in file_handles.values():
    #         output_file.close()

