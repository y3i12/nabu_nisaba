package Core::DataProcessor;

use strict;
use warnings;
use parent 'Core::BaseProcessor';
use Utils::Helper qw(validate_input format_output);

=head1 NAME

Core::DataProcessor - Concrete processor for data handling

=cut

sub new {
    my ($class, $name) = @_;
    my $self = $class->SUPER::new($name);
    $self->{processed_count} = 0;
    return bless $self, $class;
}

sub process {
    my ($self, $data) = @_;
    $self->{logger}->log("Processing data: $data");
    
    # Control statement: if/else for validation
    if (!defined $data || $data eq '') {
        die "Data cannot be empty
";
    }
    
    # Control statement: eval (try/catch) for validation
    eval {
        validate_input($data);
        1;
    } or do {
        my $error = $@;
        $self->{logger}->log("Validation failed: $error");
        die $error;
    };
    
    my $result = format_output($data);
    $self->{processed_count}++;
    return $result;
}

sub get_stats {
    my ($self) = @_;
    
    # Control statement: if/elsif/else for status
    my $status;
    if ($self->{processed_count} == 0) {
        $status = "idle";
    } elsif ($self->{processed_count} < 10) {
        $status = "active";
    } else {
        $status = "busy";
    }
    
    return {
        name => $self->{name},
        processed => $self->{processed_count},
        status => $status,
    };
}

1;
