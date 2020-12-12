#!C:/Perl64/bin/perl 

use strict;
use warnings;

use CGI;
use DBI;
use CGI::Session;
use HTML::Template;
use Digest::SHA1 qw (sha1_hex sha1_base64);

use Crypt::CBC;
use MIME::Base64;
use String::Random;

my $string;

# 1. get argument from the html form
my $CGI = new CGI();

my @field_name = ("first_name", "last_name", "tNumber", "office_name", "team_name", "position_name", "phone_number", "active");

if($CGI ->param("submit_search")){
	Search($CGI);
}	

if ($CGI ->param("add")){
	Add_data($CGI);
}

if ($CGI ->param("delete")){
	Delete_data($CGI);
}

if ($CGI ->param("update")){
	update($CGI);
}

if ($CGI ->param("login_btn")){
	login_page($CGI);
}

if ($CGI ->param("admin_search")){
	admin_Search($CGI);
}

if ($CGI ->param("logout")){
	logout($CGI);
}

if ($CGI ->param("change")){
	change_page($CGI);
}

if ($CGI ->param("submit_change")){
	change_password($CGI);
}


sub encryptString {
   my $string = shift;
   my $key=shift;
  
   my $cipher = Crypt::CBC->new(
      -key        => $key,
      -cipher     => 'Blowfish',
      -padding  => 'space',
      -add_header => 1
   );

   my $enc = $cipher->encrypt( $string  );
   return $enc; 
}

sub decryptString {
   my $string = shift;
   my $key=shift;
   
   my $cipher = Crypt::CBC->new(
      -key        => $key,
      -cipher     => 'Blowfish',
      -padding  => 'space',
      -add_header => 1
   );

   my $dec = $cipher->decrypt($string,$key);
   return $dec; 
}

sub change_page{
	my $CGI=shift;
	my $string=shift;
	my $template = HTML::Template->new(filename=> 'Change_password.tmpl');
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	$template->param("STRING" => $string);
	my $cookie=$CGI->cookie(CGISESSID=>$session->id);
	print $CGI->header(-cookie=>$cookie);
	
	print $template->output;
}

sub change_password{
	my $CGI=shift;
	my $string;
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	my $new_password=$CGI->param('New_password');
	my $confirm_password=$CGI->param('Confirm_password');
	
	if($new_password){
		if($new_password==$confirm_password){
			my $string_length=length($new_password);
			if($string_length>=8 && $string_length<=12){
				if($new_password =~ /^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])/){
					#change password in the database here
					my $dsn = "DBI:mysql:testdb";
					my $userid = $session->param("username");
					my $key=$session->param("key");
					my $mime=$session->param("password");
					my $mime_decode = decode_base64($mime);
					my $dec = decryptString($mime_decode, $key);
					my $password = $dec;
					#prepare sql for update mysql.user password, prepare sql2 for updating user-data table
					my $sql="alter user \'" . $userid."\'@\'localhost\' identified by \'".$new_password."\'";
					my $sql2="update user_data set password=\"" . $new_password. "\" where username=\"". $userid . "\"";
					
					my $error_message="Session is expired. Please login again!";
					my $dbh = DBI->connect($dsn, $userid, $password ) or die displayLoginPage($CGI, $error_message);
					
					my $stmt = $dbh->prepare($sql);
					my $stmt2=$dbh->prepare($sql2);
					#update user_data table first, then update the login password in mysql.user table
					$stmt2->execute();
					$stmt2->finish();
					
					$stmt->execute() or die $DBI::errstr;
					$stmt->finish();
					
					$dbh->disconnect();
				#end of using database
				
					$string="Change password successfully! Please login again!";
					
					change_page($CGI, $string);
				}else{
					$string="Password is invalid: Must contain combination of letter or digit";
					change_page($CGI, $string);
				}	
			}else{
				$string="Password is invalid: must be 8-12 digits";
				change_page($CGI, $string);
			}
		}else{
			$string="Please check your password. It should be exactly same in both fields";
			change_page($CGI, $string);
		}
	}else{
		$string="Your new password cannot be empty";
		change_page($CGI, $string);
	}
}

sub login_page{
	#print $CGI->header;
	
	my $CGI=shift;

	my $userid=$CGI->param('j_username');
	my $password=$CGI->param('j_password');
	
	my $user_string="";
	my $pass_string="Invalid username and password, please try again!";
	
	my $dsn = "DBI:mysql:testdb";
	
	#try to connnect to the database
	my $dbh = DBI->connect($dsn, $userid, $password ) or die displayLoginPage($CGI,$user_string,$pass_string);
	
	$dbh->disconnect();
	
	#if connecting to database is successfull, create a session for this user
	my $session=CGI::Session->new("driver:File", undef, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	my $cookie=$CGI->cookie(CGISESSID=>$session->id);
	
	#try to encrypt the password
	my $string_gen = String::Random->new;
	my $key = $string_gen->randpattern("CCcc!ccn");
	my $enc = encryptString( $password, $key );
	my $mime = encode_base64($enc);
	
	#save the encrypted password and username in session cookie
	print $CGI->header(-cookie=>$cookie);
	$session->param('username',$userid);
	$session->param('password',$mime);
	$session->param('key',$key);
	$session->save_param();
	$session->flush();
	$session->expire("15m");
	
	$user_string=$session->param('username');
	$pass_string=$session->param('password');
	
	#check whether the user is admin(root), if so, go to admin page, otherwise go to normal page.
	if($userid eq "root"){
		my $string="Log in successfully. This is admin page. Welcome ";
		$string=$string.$user_string."!";
		Display_admin_screen($CGI,$string);
	}else{
		my $string="Log in successfully. Welcome ";
		$string=$string.$user_string."!";
		Display_screen($CGI, $string);
	}
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

sub Display_screen{
	
	my $CGI=shift;
	my $string=shift;
	my $template = HTML::Template->new(filename=> 'Display_screen.tmpl');
	
	$template->param("STRING" => $string);
	
	print $template->output;
	
	
}#end of display webpage function

sub Display_admin_screen{
	my $CGI=shift;
	my $string=shift;
	my $template = HTML::Template->new(filename=> 'Display_admin_screen.tmpl');
	
	$template->param("STRING" => $string);
	
	print $template->output;
	
}#end of display admin webpage function

sub Search{
	my $CGI=shift;
	
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	#2. pass data to scalar for database connection
	
	#prepare $sql
	my $sql ="select * from test_table";
	#prepare where clause
	my %criteria =();
	
	my $field;
	
	foreach $field (@field_name){
		if ($CGI->param($field)){
			$criteria{$field}= $CGI->param($field);
		}
	}
	
	#build up where clause
	my $where_clause;
	
	if ($CGI->param('exact_match')){
		$where_clause = join(" and ", map ($_ . " = \"" . $criteria{$_} . "\"", (keys %criteria)));
	}else{
		$where_clause = join(" and ", map ($_ . " like \"%" . $criteria{$_} . "%\"", (keys %criteria)));
	}
	$where_clause =~ /(.*)/;
	$where_clause=$1;
	
	$sql = $sql . " where ". $where_clause if ($where_clause);

	#3. connect to the database
	my $dsn = "DBI:mysql:testdb";
	my $userid = $session->param("username");
	
	#get the password and decrypt the password
	my $key=$session->param("key");
	my $mime=$session->param("password");
	my $mime_decode = decode_base64($mime);
	my $dec = decryptString($mime_decode, $key);
	my $password = $dec;
	
	
	my $error_message="Session is expired. Please login again!";
	my $dbh = DBI->connect($dsn, $userid, $password ) or die displayLoginPage($CGI, $error_message);

	my $stmt = $dbh->prepare($sql);
	
	$stmt->execute() or die displayLoginPage($CGI, $error_message);

	#4. return data from database
	
	#5. return the data to display variable (Display table as HTML)
	$string="<table><tr><th>First name</th><th>Last Name</th><th>T-Number</th><th>Office</th><th>Team</th><th>Position</th><th>Phone</th><th>Active</th></tr>";
	while (my @row = $stmt->fetchrow_array()) {
		$string=$string."<tr>";
		my ($fname, $lname, $tNum, $office, $team, $position, $phone, $active)=@row;
	
		my %one_row=(
		1 => $fname,
		2 => $lname,
		3 => $tNum,
		4 => $office,
		5 => $team,
		6 => $position,
		7 => $phone,
		8 => $active,
		);
	
		for (my $i=1; $i<9; $i++){
			$string=$string . "<td>";
			$string=$string. $one_row{$i} ."</td>";
		}
	
		$string= $string. "</tr>";
	}
	$string=$string . "</table>";


	#6 disconnect the database
	$stmt->finish();
	$dbh->disconnect();

	#7.print data to HTML
	
	my $cookie=$CGI->cookie(CGISESSID=>$session->id);
	print $CGI->header(-cookie=>$cookie);
	
	Display_screen($CGI, $string);

} #end of search function

sub admin_Search{
	my $CGI=shift;
	
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	#2. pass data to scalar for database connection
	
	#prepare $sql
	my $sql ="select * from test_table";
	#prepare where clause
	my %criteria =();
	
	my $field;
	
	foreach $field (@field_name){
		if ($CGI->param($field)){
			$criteria{$field}= $CGI->param($field);
		}
	}
	
	#build up where clause
	my $where_clause;
	
	if ($CGI->param('exact_match')){
		$where_clause = join(" and ", map ($_ . " = \"" . $criteria{$_} . "\"", (keys %criteria)));
	}else{
		$where_clause = join(" and ", map ($_ . " like \"%" . $criteria{$_} . "%\"", (keys %criteria)));
	}
	$where_clause =~ /(.*)/;
	$where_clause=$1;
	
	$sql = $sql . " where ". $where_clause if ($where_clause);

	#3. connect to the database

	my $dsn = "DBI:mysql:testdb";
	my $userid = $session->param("username");
	my $key=$session->param("key");
	my $mime=$session->param("password");
	my $mime_decode = decode_base64($mime);
	my $dec = decryptString($mime_decode, $key);
	my $password = $dec;
	my $error_message="Session is expired. Please login again!";
	my $dbh = DBI->connect($dsn, $userid, $password ) or die displayLoginPage($CGI, $error_message);

	my $stmt = $dbh->prepare($sql);
	$stmt->execute() or die displayLoginPage($CGI, $error_message);


	#4. return data from database
	
	#5. return the data to display variable (Display table as HTML)
	$string="<table><tr><th>First name</th><th>Last Name</th><th>T-Number</th><th>Office</th><th>Team</th><th>Position</th><th>Phone</th><th>Active</th></tr>";
	while (my @row = $stmt->fetchrow_array()) {
		$string=$string."<tr>";
		my ($fname, $lname, $tNum, $office, $team, $position, $phone, $active)=@row;

		#$string=$string . "<td>";
		#$string=$string. $position ."</td>";
		#$string=$string. "</tr>";
	
		my %one_row=(
		1 => $fname,
		2 => $lname,
		3 => $tNum,
		4 => $office,
		5 => $team,
		6 => $position,
		7 => $phone,
		8 => $active,
		);
	
		for (my $i=1; $i<9; $i++){
			$string=$string . "<td>";
			$string=$string. $one_row{$i} ."</td>";
		}
	
		$string= $string. "</tr>";
	}
	$string=$string . "</table>";


	#6 disconnect the database
	$stmt->finish();
	$dbh->disconnect();

	#7.print data to HTML
	
	#print $CGI->header();
	#print "$sql\n";
	
	my $cookie=$CGI->cookie(CGISESSID=>$session->id);
	print $CGI->header(-cookie=>$cookie);
	
	Display_admin_screen($CGI, $string);

} #end of admin search function

sub Add_data{
#1. prepare the data array to store the field name and field value
	my $cgi=shift;
	
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	my @value_array=();
	my @missing_field=();
	my @valid_field=();
	
	my $field;
	
	my $check_tNum = $cgi->param("tNumber");
	
	my $error_message;
	#check whether the primary key tNum has value 
	if($check_tNum){
			#check tNumber format
			if($check_tNum =~ /^[Tt]\d{6,8}$/){
		
				#2. pass the value from the form
				foreach $field(@field_name){
				my $value = $cgi->param($field);
				if($value){
					push (@value_array, "'". $value. "'");
					push (@valid_field, $field);
					}
				}
			
				my $value_list ="(" . join(",",@value_array). ")";
				$value_list=~ /(.*)/;
				$value_list=$1;
	
				my $field_list = "(". join(",", @valid_field). ")";
				$field_list =~ /(.*)/;
				$field_list=$1;
			
				#3. prepare sql 
				#my $sql = "insert into test_table (First_name, Last_name, tNumber) values ('$fname', '$lname', '$tNum')";
				my $sql="insert into test_table ". $field_list . " values " . $value_list;
		
				#4. connect to the database

				my $dsn = "DBI:mysql:testdb";
				my $userid = $session->param("username");
				my $key=$session->param("key");
				my $mime=$session->param("password");
				my $mime_decode = decode_base64($mime);
				my $dec = decryptString($mime_decode, $key);
				my $password = $dec;
				$error_message="Session is expired. Please login again!";
				my $dbh = DBI->connect($dsn, $userid, $password ) or die displayLoginPage($cgi, $error_message);
				my $stmt = $dbh->prepare($sql);
				$error_message="Cannot add data as T-Number has already existed, please try again!";
				$stmt->execute() or die display_Error($cgi,$error_message);
				
				my $insert_successful="Insert successfully";
		
				#5 disconnect the database
				$stmt->finish();
				$dbh->disconnect();
				
				#print $CGI->header();
				#print "$sql";
				my $cookie=$CGI->cookie(CGISESSID=>$session->id);
				print $CGI->header(-cookie=>$cookie);
				Display_admin_screen($CGI,$insert_successful);
			
			}else{
			$error_message="T-Number should start with 't' and 6 to 8 digits, please try again";
			die display_Error($cgi,$error_message);
		
			}
		

		}else{
			$error_message ="T-Number must have value, please try again";
			die display_Error($cgi,$error_message);
		
		}

} #end of add data function

sub Delete_data{

	my $CGI=shift;
	
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	my %criteria=();    #declare hash should use round bracket
	
	my $field;

	my $error_message;
	
#   1. get value from the field
	
	foreach $field (@field_name){
		if ($CGI->param($field)){
			$criteria{$field}= $CGI->param($field);
		}
	}
	
	my $where_clause = join(" and ", map($_ . " = \"" . $criteria{$_} ."\"", (keys %criteria)));
	
	$where_clause =~ /(.*)/;
	$where_clause=$1;
	
	my $check_tNum = $CGI->param("tNumber");
	
	if ($where_clause){
		if($check_tNum){
			#2. pass data to scalar for database connection	
			my $sql = "delete from test_table";
			$sql = $sql . " where ". $where_clause if ($where_clause);
			#3. connect to the database
	
			my $dsn = "DBI:mysql:testdb";
			my $userid = $session->param("username");
			my $key=$session->param("key");
			my $mime=$session->param("password");
			my $mime_decode = decode_base64($mime);
			my $dec = decryptString($mime_decode, $key);
			my $password = $dec;
			$error_message="Session is expired. Please login again!";
			my $dbh = DBI->connect($dsn, $userid, $password ) or die displayLoginPage($CGI, $error_message);

			my $stmt = $dbh->prepare($sql);
			$stmt->execute() or die $DBI::errstr;		
			my $delete_successful="Delete rows Successfully";
	
			#   4. disconnect the database
			$stmt->finish();
			$dbh->disconnect();
	
			#print $CGI->header();
			#print $sql;
			my $cookie=$CGI->cookie(CGISESSID=>$session->id);
			print $CGI->header(-cookie=>$cookie);
		
			Display_admin_screen($CGI, $delete_successful);
		}else{
			$error_message="T-Number must have value! Please try again!";
			display_Error($CGI, $error_message);
		}
	}else{
		$error_message="You didn't select row to delete!";
		display_Error($CGI, $error_message);
	}


} #end of delete data function

sub display_Error{
	my $CGI = shift;
	my $error_message=shift;
	
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	
	#print $CGI->header();
	
	my $cookie=$CGI->cookie(CGISESSID=>$session->id);
	print $CGI->header(-cookie=>$cookie);
	
	Display_admin_screen($CGI, $error_message);

} #end of display error function

sub update{
	my $CGI = shift;
	my $session=CGI::Session->new("driver:File", $CGI, {Directory=>'../tmp/sessions'}) or die CGI::Session->errstr;
	my $error_message;
	
	my $success_message;
	
	my $check_tNum = $CGI->param("tNumber");
	
	if($check_tNum){
		#$error_message="1";
		
		if($check_tNum =~ /^[Tt]\d{6,8}$/){
			my $sql="update test_table";
			
			my %criteria =();
			
			my $field;
			
			my @update_field_name=("first_name", "last_name", "office_name", "team_name", "position_name", "phone_number", "active");
			
			foreach $field (@update_field_name){
				if ($CGI->param($field)){
					$criteria{$field}= $CGI->param($field);
				}
			}
			
			my $set_clause;
			
			$set_clause = join(" , ", map ($_ . " = \"" . $criteria{$_} . "\"", (keys %criteria)));
			
			$set_clause =~ /(.*)/;
			$set_clause=$1;
			
			if($set_clause){
			
				$sql=$sql . " set " . $set_clause;
			
				my $where_clause;
			
				my $tNum = $CGI->param("tNumber");
			
				$where_clause =" where tNumber = \"". $tNum ."\"";
			
				$sql=$sql.$where_clause; 
			
				#prepare $sql successful
			
				my $dsn = "DBI:mysql:testdb";
				my $userid = $session->param("username");
				my $key=$session->param("key");
				my $mime=$session->param("password");
				my $mime_decode = decode_base64($mime);
				my $dec = decryptString($mime_decode, $key);
				my $password = $dec;
				$error_message="Session is expired. Please login again!";
				my $dbh = DBI->connect($dsn, $userid, $password ) or die displayLoginPage($CGI, $error_message);

				my $stmt = $dbh->prepare($sql);
			
				$error_message="Cannot update data, please try again!";
				$stmt->execute() or die display_Error($CGI,$error_message);
			
				$stmt->finish();
				$dbh->disconnect();

				$success_message="Update data successfully";
				my $cookie=$CGI->cookie(CGISESSID=>$session->id);
				print $CGI->header(-cookie=>$cookie);
	
				Display_admin_screen($CGI, $success_message);
			}else{
				$error_message="You must enter data except T-Number, please try again!";
				die display_Error($CGI,$error_message);
			}
			
		}else{
			$error_message="T-Number must be T and 6 to 8 digits, please try again!";
			die display_Error($CGI, $error_message);
		}
		
	}else{
		$error_message="T-Number must have value, please try again!";
		die display_Error($CGI, $error_message);
	}
	
}

sub displayLoginPage{   
	my $CGI=shift;
	my $user_string=shift;
	my $pass_string=shift;
	
	print $CGI->header; #this is important
	my $template = HTML::Template->new(filename=> 'DisplayLoginPage.tmpl');
	
	$template->param("USER_STRING" => $user_string);
	$template->param("PASS_STRING" => $pass_string);
	
	print $template->output;
	
}
