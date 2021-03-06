#include <stdio.h>
#include "interfaces/openbmc_intf.h"
#include "gpio.h"
#include "openbmc.h"

/* ---------------------------------------------------------------------------------------------------- */
static const gchar* dbus_object_path = "/org/openbmc/buttons";
static const gchar* dbus_name        = "org.openbmc.buttons.Power";

static GDBusObjectManagerServer *manager = NULL;

//This object will use these GPIOs
GPIO gpio_button    = (GPIO){ "POWER_BUTTON" };

static gboolean
on_is_on       (Button          *btn,
                GDBusMethodInvocation  *invocation,
                gpointer                user_data)
{
  gboolean btn_state=button_get_state(btn);
  button_complete_is_on(btn,invocation,btn_state);
  return TRUE;

}

static gboolean
on_button_press       (Button          *btn,
                GDBusMethodInvocation  *invocation,
                gpointer                user_data)
{
	button_emit_button_pressed(btn);
	button_complete_sim_button_press(btn,invocation);
	return TRUE;
}
static gboolean
on_button_interrupt( GIOChannel *channel,
               GIOCondition condition,
               gpointer user_data )
{
	Button* button = object_get_button((Object*)user_data);
	printf("Power Button pressed\n");
	button_emit_button_pressed(button);
}

static void 
on_bus_acquired (GDBusConnection *connection,
                 const gchar     *name,
                 gpointer         user_data)
{
	ObjectSkeleton *object;
	//g_print ("Acquired a message bus connection: %s\n",name);
 	cmdline *cmd = user_data;
	if (cmd->argc < 2)
	{
		g_print("No objects created.  Put object name(s) on command line\n");
		return;
	}	
  	manager = g_dbus_object_manager_server_new (dbus_object_path);
  	int i=0;
	gchar *s;
	s = g_strdup_printf ("%s/%s",dbus_object_path,cmd->argv[1]);
	object = object_skeleton_new (s);
	g_free (s);

	Button* button = button_skeleton_new ();
	object_skeleton_set_button (object, button);
	g_object_unref (button);

	//define method callbacks
	g_signal_connect (button,
                   "handle-is-on",
                   G_CALLBACK (on_is_on),
                   NULL); /* user_data */
	g_signal_connect (button,
                    "handle-sim-button-press",
                    G_CALLBACK (on_button_press),
                    NULL); /* user_data */

		
	/* Export the object (@manager takes its own reference to @object) */
	g_dbus_object_manager_server_export (manager, G_DBUS_OBJECT_SKELETON (object));
	g_object_unref (object);

	/* Export all objects */
	g_dbus_object_manager_server_set_connection (manager, connection);

	// get gpio device paths
	int rc = GPIO_OK;
	do {
		rc = gpio_init(connection,&gpio_button);
		if (rc != GPIO_OK) { break; }
		rc = gpio_open_interrupt(&gpio_button,on_button_interrupt,object);
		if (rc != GPIO_OK) { break; }
	} while(0);
	if (rc != GPIO_OK)
	{
		printf("ERROR PowerButton: GPIO setup (rc=%d)\n",rc);
	} 

}

static void
on_name_acquired (GDBusConnection *connection,
                  const gchar     *name,
                  gpointer         user_data)
{
}

static void
on_name_lost (GDBusConnection *connection,
              const gchar     *name,
              gpointer         user_data)
{
}


gint
main (gint argc, gchar *argv[])
{
  GMainLoop *loop;

  cmdline cmd;
  cmd.argc = argc;
  cmd.argv = argv;

  guint id;
  loop = g_main_loop_new (NULL, FALSE);

  id = g_bus_own_name (DBUS_TYPE,
                       dbus_name,
                       G_BUS_NAME_OWNER_FLAGS_ALLOW_REPLACEMENT |
                       G_BUS_NAME_OWNER_FLAGS_REPLACE,
                       on_bus_acquired,
                       on_name_acquired,
                       on_name_lost,
                       &cmd,
                       NULL);

  g_main_loop_run (loop);
  
  g_bus_unown_name (id);
  g_main_loop_unref (loop);
  return 0;
}
