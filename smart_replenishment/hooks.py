app_name = "smart_replenishment"
app_title = "Smart Replenishment"
app_publisher = "analyze inventory levels, consumption patterns, and supplier information to automatically generate purchase"
app_description = "a Smart Replenishment Module for a pharmacy supply chain platform. This module should"
app_email = "omarsalama102@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "smart_replenishment",
# 		"logo": "/assets/smart_replenishment/logo.png",
# 		"title": "Smart Replenishment",
# 		"route": "/smart_replenishment",
# 		"has_permission": "smart_replenishment.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/smart_replenishment/css/smart_replenishment.css"
# app_include_js = "/assets/smart_replenishment/js/smart_replenishment.js"

# include js, css files in header of web template
# web_include_css = "/assets/smart_replenishment/css/smart_replenishment.css"
# web_include_js = "/assets/smart_replenishment/js/smart_replenishment.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "smart_replenishment/public/scss/website"

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

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "smart_replenishment/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "smart_replenishment.utils.jinja_methods",
# 	"filters": "smart_replenishment.utils.jinja_filters"
# }

# Installation
# ------------

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Item-pharmacy_inventory_section",
                    "Item-average_daily_consumption",
                    "Item-consumption_calculation_period",
                    "Item-last_consumption_update",
                    "Item-pharmacy_column_1",
                    "Item-global_reorder_point",
                    "Item-maximum_stock_level",
                    "Item-safety_stock_days",
                    "Item-pharmacy_requirements_section",
                    "Item-requires_prescription",
                    "Item-is_controlled_substance",
                    "Item-controlled_substance_schedule",
                    "Item-pharmacy_column_2",
                    "Item-storage_temperature",
                    "Item-drug_category",
                    "Item-preferred_supplier_section",
                    "Item-preferred_supplier",
                    "Item-supplier_reliability_score",
                ],
            ]
        ],
    }
]

# Uninstallation
# ------------

# before_uninstall = "smart_replenishment.uninstall.before_uninstall"
# after_uninstall = "smart_replenishment.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "smart_replenishment.utils.before_app_install"
# after_app_install = "smart_replenishment.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "smart_replenishment.utils.before_app_uninstall"
# after_app_uninstall = "smart_replenishment.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "smart_replenishment.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
doc_events = {
    "Item": {
        "on_update": "smart_replenishment.api.calculate_item_reorder_levels",
    }
}

# Scheduled Tasks
# ---------------
scheduler_events = {
    "daily": [
        "smart_replenishment.api.calculate_reorder_points_all_items",
    ],
    "hourly": [
        "smart_replenishment.api.generate_replenishment_recommendations",
    ],
}

# Testing
# -------

# before_tests = "smart_replenishment.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "smart_replenishment.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "smart_replenishment.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["smart_replenishment.utils.before_request"]
# after_request = ["smart_replenishment.utils.after_request"]

# Job Events
# ----------
# before_job = ["smart_replenishment.utils.before_job"]
# after_job = ["smart_replenishment.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"smart_replenishment.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

