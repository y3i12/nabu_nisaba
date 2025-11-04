#!/usr/bin/env perl

use strict;
use warnings;
use lib '.';

use Core::DataProcessor;
use Utils::Logger;

=head1 NAME

main.pl - Main entry point demonstrating the system

=cut

sub main {
    my $logger = Utils::Logger->new("Main");
    $logger->log("Starting application");
    
    my $processor = Core::DataProcessor->new("MainProcessor");
    
    # Control statement 1: if/elsif/else block
    my $test_data = "test data";
    if (length($test_data) > 20) {
        $logger->log("Large data detected");
        $test_data = substr($test_data, 0, 20);
    } elsif (length($test_data) < 5) {
        $logger->log("Small data detected");
        $test_data = "default";
    } else {
        $logger->log("Normal data size");
    }
    
    # Control statement 2: try/catch block (eval in Perl)
    my $result;
    eval {
        $result = $processor->process($test_data);
        $logger->log("Result: $result");
        1;
    } or do {
        my $error = $@ || 'Unknown error';
        if ($error =~ /validation/i) {
            $logger->log("Validation error: $error");
        } else {
            $logger->log("Processing error: $error");
        }
        $result = undef;
    };
    
    # Always execute (finally equivalent)
    $logger->log("Processing attempt completed");
    
    # Control statement 3: for loop
    my @test_items = ("item1", "item2", "item3");
    for my $item (@test_items) {
        if ($item) {
            $processor->process($item);
        }
    }
    
    # Control statement 4: while loop
    my $retry_count = 0;
    my $max_retries = 3;
    while ($retry_count < $max_retries) {
        my $stats = $processor->get_stats();
        if ($stats->{processed} > 0) {
            last;
        }
        $retry_count++;
    }
    
    # Control statement 5: given/when (switch) - Perl 5.10+
    my $status_code = 200;
    use feature 'switch';
    no warnings 'experimental::smartmatch';
    given ($status_code) {
        when (200) { $logger->log("Success"); }
        when (404) { $logger->log("Not found"); }
        default    { $logger->log("Other status"); }
    }
    
    my $stats = $processor->get_stats();
    $logger->log("Stats: name=$stats->{name}, processed=$stats->{processed}");
}

main() unless caller;

1;
