"use strict";


async function postData(url = '', data = '') {
  const response = await fetch(url, {
    method: 'POST', // *GET, POST, PUT, DELETE, etc.
    mode: 'cors', // no-cors, *cors, same-origin
    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
	body: data
  });
  var result =  await response;
  return await result.text();
}


function InitXMLHttp(query, callbackFunc) //!!! legacy
{
	// code for IE7+, Firefox, Chrome, Opera, Safari
	var xmlhttp;
	if (window.XMLHttpRequest) xmlhttp=new XMLHttpRequest();
	else xmlhttp=new ActiveXObject('Microsoft.XMLHTTP'); // code for old IE7

	xmlhttp.onreadystatechange = function()
	{
		if (xmlhttp.readyState==4 && xmlhttp.status==200) callbackFunc(xmlhttp.responseText);
	}
	xmlhttp.open('GET',query,true);
	xmlhttp.send();
}

function StripSpecialChars(str) {
	return str.replace(/[&\/\\#$~'"<>{}]/g, ' ');
}



function PurifyFormData(formElements) {
	for (var i=0;i<formElements.length;i++)	{
		if ((formElements[i].value!="") && (formElements[i].type=="text")) formElements[i].value = StripSpecialChars(formElements[i].value);
	}
}


function OrdinaryFormCheck(theForm,list)
{
	for (var i=0; i<list.length; i++)
	{
		var elm = theForm.elements[list[i]];
		if (!NonEmptyFieldValidator(elm))
		{
			if (NodeList.prototype.isPrototypeOf(elm)) elm = elm[0]; 
			return "Required field '"+elm.title+"' is either omitted or incorrect.";
		}
	}
	return ""; //return empty string instead of underfined.
}

function EmailChecker(theEmail)
{
	var result = true;
	var at=theEmail.indexOf('@');
	var last_at=theEmail.lastIndexOf('@');
	var point=theEmail.lastIndexOf('.');
	var lngth=theEmail.length;
	var dist_at=point-at;
	var dist=lngth-point;
	if ((at<1)||(dist<2)||(dist_at<1)||(last_at>at)) result=false;
	return result;
}

function NonEmptyFieldValidator(theElement)
{
//checks that the value in not en empty string 
	var result = true;
	if (!theElement) console.log(theElement + ' is missing');
	else
	{
		switch (theElement.type)
		{
			case 'select-one':
				if (!theElement.options[theElement.options.selectedIndex].value)  result = false;
				break;
			case 'text':
			case 'textarea':
			default:
				if (!theElement.value) result = false;
				break;
		}
	}
	return result;
}	
