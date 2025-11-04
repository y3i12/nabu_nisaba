package Utils::Logger;

use strict;
use warnings;

=head1 NAME

Utils::Logger - Simple logger class for demonstration

=cut

sub new {
    my ($class, $name) = @_;
    my $self = {
        name => $name,
        enabled => 1,
    };
    return bless $self, $class;
}

sub log {
    my ($self, $message) = @_;
    if ($self->{enabled}) {
        print "[$self->{name}] $message\n";
    }
}

sub disable {
    my ($self) = @_;
    $self->{enabled} = 0;
}

1;
