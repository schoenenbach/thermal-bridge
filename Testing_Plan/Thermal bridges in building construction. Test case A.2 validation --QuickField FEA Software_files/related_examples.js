"use strict";

function GetExamlesList(keyword)
{
	var query = '../examples/example_list.php?search_phrase='+keyword;
	
	InitXMLHttp(query,DisplaySearchResuls); //async
	
	function DisplaySearchResuls(text)
	{
		var json_array = JSON.parse(text);
		if (json_array.length>1) //one is the example itself
		{
			var list = document.getElementById('moreExamples');
			var listText = "<p><b>Related examples</b>";
			for (var i=0;i<Math.min(json_array.length,6);i++)
			{
				var node = json_array[i];	
				if ("/"+ node.HTMLlink == window.location.pathname) continue;
				listText += "<br><a href='../" + node.HTMLlink + "'>" + node.name + "</a>";
			}
			listText += "<br>See more examples in the <a href='../examples/'>Examples gallery</a>";
			
			list.innerHTML = listText;
		}
	}
}


function ReadKeyword()
{
	var scripts = document.getElementsByTagName('script');
	for (var i=0;i<scripts.length;i++)
	{
		if (scripts[i]["type"]=="application/ld+json")
		{
			var inside = scripts[i].innerHTML;
			var obj = JSON.parse(inside);
			if (obj["@type"]=="DigitalDocument")
			{
				return obj["keywords"].split(/[ ,]/g)[0]; //first word	
			}
		}
	}
}



window.onload = GetExamlesList(ReadKeyword());