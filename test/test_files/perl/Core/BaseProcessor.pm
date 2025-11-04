package Core::BaseProcessor;

use strict;
use warnings;
use Utils::Logger;

=head1 NAME

Core::BaseProcessor - Base processor with common functionality

=cut

sub new {
    my ($class, $name) = @_;
    my $self = {
        name => $name,
        logger => Utils::Logger->new($name),
    };
    return bless $self, $class;
}

sub process {
    my ($self, $data) = @_;
    die "Subclasses must implement process()";
}

1;
