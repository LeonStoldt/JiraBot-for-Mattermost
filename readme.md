# Jira Bot for Mattermost
> This python script uses the jira and Mattermost api to extract changes in jira and posts them to your mattermost channel.
> You can toggle which changes you want to get!
> The following aspects are posted to Mattermost:
> * priority
> * status
> * assignee
> * description
> * attachments
> * comments
> * issue type
> * UX-Design


## Requirements

* python 3.4 or higher

## Installation

OS X & Linux:

```sh
$ pip install mattermostdriver
```

```sh
$ pip install jira
```

```sh
$ pip install DateTime
```

```sh
$ pip install urllib3
```

```sh
$ pip install simplejson
```

```sh
$ pip install requests
```

## Configure

* Timestamp.json
>	configure the timestamp.json to just get updates from now:
>	{"timestamp": "yyyy-MM-ddTHH:mm:00.11252800"}
>	just change yyyy, MM, dd, HH and mm

* change webhook data:
> replace your data like it is signed in the webhook.py
> ## HINT: Build your jql string carefully to not get spamed! Or reduce the maxResults. 


## Start the script

I would suggest a cronjob to run the script
> to edit your cronjob
```sh
crontab -e
```
> to execute it at every 2nd minute past every hour from 7 through 19 on every day-of-week from Monday through Friday add: 
```sh
*/2 7-19 * * 1-5 python $HOME/cronlogs/jira_bot.py > $HOME/cronlogs/jiraBot.log 2>&1
```
> the suffix 2>&1 is logging even errors to the jiraBot.log
>
> for help go to https://crontab.guru/


## Usage example

Use the script to update yourself easily with Mattermost.
If you don't want to get messages for all your Project issues, just search for you as assignee as example.
Or search for issues with Backlog / Ready for Dev / ... as status.


## Information

## This script is not finished yet and it can happen that some Bugs occur!


## Meta

Leon Stoldt – [@Github](https://github.com/LeonStoldt)

Distributed under the MIT license. See ``LICENSE`` for more information.

## Contributing

1. Fork it 
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request

