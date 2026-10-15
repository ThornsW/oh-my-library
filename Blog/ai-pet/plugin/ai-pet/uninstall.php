<?php
/**
 * 在后台「删除」插件时运行（停用不会触发）：删掉插件建的聊天记录表、设置、API key、缓存和定时任务。
 */

if ( ! defined( 'ABSPATH' ) || ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

global $wpdb;
$wpdb->query( "DROP TABLE IF EXISTS {$wpdb->prefix}aipet_log" ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery.SchemaChange
foreach ( array( 'aipet_settings', 'aipet_api_key', 'aipet_db_version' ) as $aipet_option ) {
	delete_option( $aipet_option );
}
$wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE '\\_transient\\_aipet\\_%' OR option_name LIKE '\\_transient\\_timeout\\_aipet\\_%'" );
wp_clear_scheduled_hook( 'aipet_log_cleanup' );
