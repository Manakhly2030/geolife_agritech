from . import __version__ as app_version

app_name = "geolife_agritech"
app_title = "Geolife Agritech"
app_publisher = "Erevive Technologies"
app_description = "Application for Geolife Agritech"
app_email = "laxmantandon@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/geolife_agritech/css/geolife_agritech.css"
# app_include_js = "/assets/geolife_agritech/js/geolife_agritech.js"

# include js, css files in header of web template
# web_include_css = "/assets/geolife_agritech/css/geolife_agritech.css"
# web_include_js = "/assets/geolife_agritech/js/geolife_agritech.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "geolife_agritech/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "geolife_agritech.utils.jinja_methods",
#	"filters": "geolife_agritech.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "geolife_agritech.install.before_install"
# after_install = "geolife_agritech.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "geolife_agritech.uninstall.before_uninstall"
# after_uninstall = "geolife_agritech.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "geolife_agritech.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
#	"all": [
#		"geolife_agritech.tasks.all"
#	],
	"daily": [
		"geolife_agritech.v1.geolife_api.daily_day_end"
	],
    "cron":
		{"00 03 * * 1-7": [
			"geolife_agritech.v1.geolife_api.Evening_7pm_Notifications"
			]
		},
	# "hourly": [
	# 	"geolife_agritech.v1.geolife_api.Evening_7pm_Notifications"
	# ],
#	"weekly": [
#		"geolife_agritech.tasks.weekly"
#	],
#	"monthly": [
#		"geolife_agritech.tasks.monthly"
#	],
}

# Testing
# -------

# before_tests = "geolife_agritech.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "geolife_agritech.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "geolife_agritech.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"geolife_agritech.auth.validate"
# ]

