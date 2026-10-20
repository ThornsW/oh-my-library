<?php
/**
 * Plugin Name:       AI 宠物
 * Plugin URI:        https://github.com/ThornsW/oh-my-library/tree/main/Blog/ai-pet
 * Description:       给博客左下角加一个会聊天的看板角色（自备图片或 JS 角色文件）。它会根据当前页面和全站文章推荐站内内容，聊天后端是任意 OpenAI 兼容接口。
 * Version:           0.4.1
 * Author:            Thorns
 * Author URI:        https://github.com/ThornsW
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Requires PHP:      8.0
 * Requires at least: 6.5
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// 也是 wp_enqueue_* 的缓存参数：改了 CSS/JS 就提升它。
define( 'AIPET_VERSION', '0.4.1' );
define( 'AIPET_DIR', plugin_dir_path( __FILE__ ) );
define( 'AIPET_URL', plugin_dir_url( __FILE__ ) );

require AIPET_DIR . 'includes/settings.php';
require AIPET_DIR . 'includes/character.php';
require AIPET_DIR . 'includes/context.php';
require AIPET_DIR . 'includes/chat.php';
require AIPET_DIR . 'includes/log.php';

register_activation_hook( __FILE__, 'aipet_maybe_install' );
register_deactivation_hook( __FILE__, 'aipet_unschedule' );

function aipet_unschedule() {
	wp_clear_scheduled_hook( 'aipet_log_cleanup' );
}

add_action( 'wp_enqueue_scripts', 'aipet_enqueue' );

function aipet_enqueue() {
	$kind = aipet_character_kind();
	if ( ! aipet_opt( 'enabled' ) || '' === $kind ) {
		return; // 没有角色时前台什么都不输出
	}
	$deps = array();
	if ( 'js' === $kind ) {
		$file = aipet_character_file();
		wp_enqueue_script( 'ai-pet-character', $file['url'], array(), $file['ver'], array( 'in_footer' => true, 'strategy' => 'defer' ) );
		$deps[] = 'ai-pet-character';
	}
	wp_enqueue_style( 'ai-pet', AIPET_URL . 'assets/pet.css', array(), AIPET_VERSION );
	wp_enqueue_script( 'ai-pet', AIPET_URL . 'assets/pet.js', $deps, AIPET_VERSION, array( 'in_footer' => true, 'strategy' => 'defer' ) );
	$config = array(
		'rest'      => esc_url_raw( rest_url( 'ai-pet/v1/chat' ) ),
		'chat'      => aipet_chat_ready(),
		'home'      => esc_url_raw( home_url( '/' ) ),
		'anime'     => esc_url_raw( (string) aipet_anime_page_url() ),
		'site'      => wp_specialchars_decode( get_bloginfo( 'name' ), ENT_QUOTES ),
		'name'      => aipet_opt( 'pet_name' ),
		'width'     => (int) aipet_opt( 'pet_width' ),
		'images'    => 'image' === $kind ? aipet_character_images() : (object) array(),
		'pixel'     => (bool) aipet_opt( 'img_pixel' ),
		'colors'    => array( aipet_opt( 'color_light' ), aipet_opt( 'color_dark' ) ),
		'dark'      => aipet_opt( 'dark_mode' ),
		'hideBelow' => (int) aipet_opt( 'hide_below' ),
		'notice'    => aipet_opt( 'log_enabled' ) && aipet_opt( 'notice' ),
	);
	wp_add_inline_script( 'ai-pet', 'window.AIPET = ' . wp_json_encode( $config ) . ';', 'before' );
}
