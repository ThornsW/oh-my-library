<?php
/**
 * 角色：插件本身不带角色，站长二选一提供。
 * - JS 角色文件：放在 wp-content/uploads/ai-pet/character.js，定义 window.AIPET_CHARACTER（接口见 README）。
 *   放在 uploads 里是为了更新或重装插件时不会被覆盖。有这个文件时优先用它。
 * - 图片：在「AI 宠物 → 设置」里给每种表情选一张图，至少要有「普通」。
 * 两样都没有时前台不显示，后台给管理员提示。
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/** 图片角色的各个位置：设置里的键是 img_<位置>。 */
const AIPET_IMAGE_SLOTS = array(
	'normal'    => '普通（必填）',
	'happy'     => '开心',
	'shy'       => '害羞',
	'surprised' => '惊讶',
	'sleepy'    => '困了',
	'talk'      => '说话（张嘴）',
	'blink'     => '眨眼',
);

/** JS 角色文件的路径和网址；没有这个文件时返回 null。 */
function aipet_character_file() {
	$up   = wp_upload_dir( null, false );
	$path = trailingslashit( $up['basedir'] ) . 'ai-pet/character.js';
	if ( ! is_file( $path ) ) {
		return null;
	}
	return array(
		'path' => $path,
		'url'  => trailingslashit( $up['baseurl'] ) . 'ai-pet/character.js',
		'ver'  => (string) filemtime( $path ),
	);
}

/** 已填的角色图片：位置 => 网址。没有「普通」图时返回空数组。 */
function aipet_character_images() {
	$out = array();
	foreach ( array_keys( AIPET_IMAGE_SLOTS ) as $slot ) {
		$url = (string) aipet_opt( 'img_' . $slot );
		if ( '' !== $url ) {
			$out[ $slot ] = $url;
		}
	}
	return isset( $out['normal'] ) ? $out : array();
}

/** 当前用哪种角色：js、image，或者空字符串（没有角色）。 */
function aipet_character_kind() {
	if ( aipet_character_file() ) {
		return 'js';
	}
	return aipet_character_images() ? 'image' : '';
}

add_action( 'admin_notices', 'aipet_character_notice' );

/** 没有角色时，在仪表盘、插件页和本插件的页面提示管理员。 */
function aipet_character_notice() {
	if ( ! current_user_can( 'manage_options' ) || ! aipet_opt( 'enabled' ) || '' !== aipet_character_kind() ) {
		return;
	}
	$screen = get_current_screen();
	// 子菜单页的 screen id 以菜单名开头（中文会被转码），所以按是否含 ai-pet 判断
	if ( ! $screen || ! ( in_array( $screen->id, array( 'dashboard', 'plugins' ), true ) || false !== strpos( $screen->id, 'ai-pet' ) ) ) {
		return;
	}
	printf(
		'<div class="notice notice-warning"><p>AI 宠物还没有角色，前台暂时不显示。请到 <a href="%s">AI 宠物 → 设置</a> 上传角色图片，或放一个 JS 角色文件。</p></div>',
		esc_url( admin_url( 'admin.php?page=ai-pet-settings' ) )
	);
}
