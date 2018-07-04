# Mattermost
url = 'replace_your_mattermost_url' #TODO
token = 'replace_mattermost_token_of_bot' #TODO
scheme = 'https'
port = 443 # may replace Port or scheme
verify = False
channel = "replace_channel" #TODO
botName = "JiraBot" # can change BotName

# JIRA
jiraUrl = 'https://replace_your_jira_url' #TODO
username = 'replace_jira_username' #TODO
password = 'replace_jira_password' #TODO
jqlQueryString = '{}browse/'.format(jiraUrl)
projectSearchString = 'project=XY and updated>"{}" order by key desc' #KEEP UPDATED!! #TODO build your own query string for jql(https://confluence.atlassian.com/jiracore/blog/2015/07/search-jira-like-a-boss-with-jql)
expand = 'renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations' # may remove details you don't need
maxResults = 200 # change max result of tickets you get from jql query
# The following states are for configuring the message. You can turn on or off what aspect you want to post and change it really quickly
# hint: the short summary of an issue is default. You cannot turn off this state.
postAssignee = True
postStatus = True
postAttachment = True
postDescription = True
postComments = True
postUXDesign = True
postIssueType = True
postPriority = True

# Filesystem
pathToFile = "$HOME/cronlogs/timestamp.json" #TODO link your timestamp.json file to get the updates since last execution.
