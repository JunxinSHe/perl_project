#!C:/Perl64/bin/perl 

use strict;
use warnings;

use CGI;
use DBI;
use CGI::Session;
use HTML::Template;
use Email::Valid;
use MIME::Entity;
use Net::SMTP;




my $CGI = new CGI();

if($CGI ->param("submit_btn")){
	forgot($CGI);
}	



sub forgot{
	my $CGI=shift;
	my $username=$CGI->param("username");
	my $email=$CGI->param("email");
	my $string;
	
	#my $dbh = DBI->connect("dbi:mysql:mysql", "root", "32816980" ) or die "Cannot connect to db: $DBI::errstr";
	
	if(Email::Valid->address($email)){
		if($username){
			my $dbh = DBI->connect("dbi:mysql:mysql", "root", "32816980" ) or die "Cannot connect to db: $DBI::errstr";
			my $sql="select * from testdb.user_data where username=\'".$username."\'";
			my $stmt = $dbh->prepare($sql);
			$string="Cannot connect to the database!";
			$stmt->execute() or die forgot_page($CGI, $string);
			if(my $info = $stmt->fetchrow_hashref){
				if($info->{email}=~ /$email/i){
					$string="Username is valid, please check your email!";
					$stmt->finish();
					$dbh->disconnect();
					forgot_page($CGI,$string);
					#send a email containing reset password page link
					sendEmail($username,$email);
					
				}else{
					$string="Email address does not match! Please check again!";
					$stmt->finish();
					$dbh->disconnect();
					forgot_page($CGI,$string);
				}
			}else{
				$string="Username is not valid, please enter again!";
				$stmt->finish();
				$dbh->disconnect();
				forgot_page($CGI,$string);
			}
		}else{
			$string="Username cannot be empty, please enter a valid username";
			forgot_page($CGI, $string);
		}
	}else{
		$string="$email doesn't appear to be a valid email address. Please enter a valid email address!";
		forgot_page($CGI,$string);
	}

}

sub forgot_page{
	my $CGI=shift;
	my $string=shift;
	
	my $template = HTML::Template->new(filename=> 'forgot_page.tmpl');
	
	$template->param("STRING" => $string);
	print $CGI->header;
	print $template->output;
}

sub sendEmail{
	# from is your email address
	# to is who you are sending your email to
	# subject will be the subject line of your email
	my $username=shift;
	my $to=shift;
	my $from = 'junxin.standey@hotmail.com';
	
	my $subject = 'Reset your password';

	# Create the MIME message that will be sent. Check out MIME::Entity on CPAN for more details
	my $mime = MIME::Entity->build(Type  => 'multipart/alternative',
								Encoding => '-SUGGEST',
								From => $from,
								To => $to,
								Subject => $subject
								);
# Create the body of the message (a plain-text and an HTML version).
# text is your plain-text email
# html is your html version of the email
# if the receiver is able to view html emails then only the html
# email will be displayed
	my $text = "Hi!\nHow are you?\n";
	my $html = <<EOM;
<html>
  <head></head>
  <body>
    <p>Hi! $username<br>
       How are you?<br>
    </p>
	<p>
		Please click the link to reset your password! <a href="http://localhost/reset.html">Link</a>
	</p>
	<p>Best Regards</p>
	
  </body>
</html>
EOM

# attach the body of the email
	$mime->attach(Type => 'text/plain',
				Encoding =>'-SUGGEST',
				Data => $text);

	$mime->attach(Type => 'text/html',
				Encoding =>'-SUGGEST',
				Data => $html);


# Login credentials 
	my $username = 'apikey';
	my $password = "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";

# Open a connection to the SendGrid mail server, can only use 587 port
	my $smtp = Net::SMTP->new('smtp.sendgrid.net',
							Port=> 587,
							Timeout => 20,
							Hello => "hotmail.com");

# Authenticate
	$smtp->auth($username, $password);

# Send the rest of the SMTP stuff to the server
	$smtp->mail($from);
	$smtp->to($to);
	$smtp->data($mime->stringify);
	$smtp->quit();
	
}




