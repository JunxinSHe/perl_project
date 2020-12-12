#!C:/Perl64/bin/perl 

use strict;
use warnings;

use CGI;
use DBI;
use CGI::Session;
use HTML::Template;
use Email::Valid;

my $CGI = new CGI();

if($CGI ->param("submit_reset")){
	resetPassword($CGI);
}	

if ($CGI ->param("logout")){
	logout($CGI);
}

sub logout{
	my $CGI=shift;
	my $string="Log out successfully! ";
	
	#clear all session
	my $session=CGI::Session->new("driver:File", undef, {Directory=>'../tmp/sessions'});
	$session->delete();
	$session->flush();
	
	print $CGI->header;
	
	print $string;
	print qq`
	<a href="http://localhost/first_project.html">Back to home page</a>
	`
	
}

sub reset_Page{
	my $CGI=shift;
	my $string=shift;
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	my $template = HTML::Template->new(filename=> 'reset_page.tmpl');
	$template->param("STRING" => $string);
	my $cookie=$CGI->cookie(CGISESSID=>$session->id);
	print $CGI->header(-cookie=>$cookie);
	print $template->output;
}

sub resetPassword{
	my $CGI=shift;
	my $string=shift;
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	my $username=$CGI->param('username');
	my $new_password=$CGI->param('New_password');
	my $confirm_password=$CGI->param('Confirm_password');
	
	
	
	if($username){
		my $dbh = DBI->connect("dbi:mysql:mysql", "root", "32816980" ) or die "Cannot connect to db: $DBI::errstr";
		my $sql="select * from testdb.user_data where username=\'".$username."\'";
		my $stmt = $dbh->prepare($sql);
		$string="Cannot connect to the database!";
		$stmt->execute() or die reset_Page($CGI,$string);
		if(my $info = $stmt->fetchrow_hashref){
			$stmt->finish();
			$dbh->disconnect();
			
			if($new_password){
				
				if($new_password==$confirm_password){  
					
					my $string_length=length($new_password);
					if($string_length>=8 && $string_length<=12){
						
						if($new_password =~ /^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])/){
							
							#change password in the database here
							my $dsn = "DBI:mysql:testdb";
							
							#prepare sql for update mysql.user password, prepare sql2 for updating user-data table
							my $sql="alter user \'" . $username."\'@\'localhost\' identified by \'".$new_password."\'";
							my $sql2="update user_data set password=\"" . $new_password. "\" where username=\"". $username . "\"";
							
							#with admin(root) access, user can reset their password
							$string="cannot connect to database";
							$dbh = DBI->connect("dbi:mysql:testdb", "root", "32816980" ) or die reset_Page($CGI, $string);
						
							my $stmt = $dbh->prepare($sql);
							my $stmt2=$dbh->prepare($sql2);
							#update user_data table first, then update the login password in mysql.user table
							$stmt2->execute();
							$stmt2->finish();
					
							$stmt->execute();
							$stmt->finish();
						
							$dbh->disconnect();
							
							$string="Reset password successfully! Please log in again!";
							reset_Page($CGI, $string);
							
						}else{
							$string="Password is invalid: Must contain combination of letter or digit";
							reset_Page($CGI, $string);
						}
					}else{
						$string="Password is invalid: must be 8-12 digits";
						reset_Page($CGI, $string);
					}
				}else{
					$string="Please check your password. It should be exactly same in both fields";
					reset_Page($CGI,$string);
				}
			}else{
				$string="Your new password cannot be empty!";
				reset_Page($CGI, $string);
			}
		}else{
			$string="Username is not valid, please try again!";
			$stmt->finish();
			$dbh->disconnect();
			reset_Page($CGI,$string);
		}
	}else{
		$string="Username cannot be empty!";
		reset_Page($CGI, $string);
	}
}







