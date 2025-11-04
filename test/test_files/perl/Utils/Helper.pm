package Utils::Helper;

use strict;
use warnings;
use Exporter 'import';

our @EXPORT_OK = qw(validate_input format_output);

=head1 NAME

Utils::Helper - Helper utility functions for validation and formatting

=cut

sub validate_input {
    my ($data) = @_;
    if (!defined $data) {
        die "Data cannot be undefined";
    }
    return 1;
}

sub format_output {
    my ($value) = @_;
    return uc($value);
}

1;
