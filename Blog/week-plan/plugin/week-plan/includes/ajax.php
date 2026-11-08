<?php
/**
 * 拖拽和打勾的写入端点。
 *
 * 每个端点都先验 nonce 再验权限,两道都过才动数据。
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

const WEEKPLAN_NONCE = 'weekplan_action';

function weekplan_register_ajax(): void {
	$actions = array( 'add', 'move', 'remove', 'reorder', 'toggle', 'detail', 'create', 'save', 'delete', 'tag_save', 'tag_delete', 'batch', 'shift', 'preview', 'memo', 'view' );
	foreach ( $actions as $action ) {
		add_action( "wp_ajax_weekplan_$action", "weekplan_ajax_$action" );
	}
}

/** 所有端点的共同门禁。 */
function weekplan_ajax_guard(): void {
	check_ajax_referer( WEEKPLAN_NONCE, 'nonce' );
	if ( ! current_user_can( 'manage_options' ) ) {
		wp_send_json_error( array( 'message' => '权限不足。' ), 403 );
	}
}

function weekplan_ajax_reply( mixed $result ): void {
	if ( is_wp_error( $result ) ) {
		wp_send_json_error( array( 'message' => $result->get_error_message() ), 400 );
	}
	wp_send_json_success( is_array( $result ) ? $result : array() );
}

function weekplan_post_int( string $key ): int {
	return isset( $_POST[ $key ] ) ? (int) $_POST[ $key ] : 0;
}

function weekplan_post_text( string $key ): string {
	return isset( $_POST[ $key ] ) ? sanitize_text_field( wp_unslash( $_POST[ $key ] ) ) : '';
}

function weekplan_ajax_add(): void {
	weekplan_ajax_guard();

	$todo_id = weekplan_post_int( 'todo_id' );
	$date    = weekplan_post_text( 'date' );
	$result  = weekplan_add_schedule( $todo_id, $date );

	if ( is_wp_error( $result ) ) {
		weekplan_ajax_reply( $result );
	}

	weekplan_ajax_reply(
		array(
			'schedule_id' => $result,
			'html'        => weekplan_card_html(
				array(
					'schedule_id' => $result,
					'date'        => $date,
					'done'        => false,
					'todo'        => weekplan_todo_summary( $todo_id ),
				)
			),
		)
	);
}

function weekplan_ajax_move(): void {
	weekplan_ajax_guard();
	weekplan_ajax_reply( weekplan_move_schedule( weekplan_post_int( 'schedule_id' ), weekplan_post_text( 'date' ) ) );
}

function weekplan_ajax_remove(): void {
	weekplan_ajax_guard();
	weekplan_remove_schedule( weekplan_post_int( 'schedule_id' ) );
	weekplan_ajax_reply( array() );
}

function weekplan_ajax_reorder(): void {
	weekplan_ajax_guard();

	$raw = isset( $_POST['ids'] ) ? (array) wp_unslash( $_POST['ids'] ) : array();
	$ids = array_map( 'intval', $raw );

	weekplan_ajax_reply( weekplan_reorder_day( weekplan_post_text( 'date' ), $ids ) );
}

function weekplan_ajax_toggle(): void {
	weekplan_ajax_guard();
	weekplan_ajax_reply( weekplan_toggle_done( weekplan_post_int( 'schedule_id' ) ) );
}

/* ---------- 待办本身 ---------- */

function weekplan_ajax_detail(): void {
	weekplan_ajax_guard();

	ob_start();
	weekplan_render_detail( weekplan_post_int( 'todo_id' ) );
	weekplan_ajax_reply( array( 'html' => (string) ob_get_clean() ) );
}

function weekplan_ajax_create(): void {
	weekplan_ajax_guard();

	$id = weekplan_create_todo( weekplan_post_text( 'title' ) );
	if ( is_wp_error( $id ) ) {
		weekplan_ajax_reply( $id );
	}

	weekplan_ajax_reply(
		array(
			'todo_id'     => $id,
			'detail_html' => weekplan_capture( 'weekplan_render_detail', $id ),
		)
	);
}

/**
 * 详情栏逐项保存,一次只送一个字段。
 * tags 和 subtasks 是结构化的,单独解一下。
 */
function weekplan_ajax_save(): void {
	weekplan_ajax_guard();

	$id    = weekplan_post_int( 'todo_id' );
	$field = weekplan_post_text( 'field' );

	$allowed = array( 'title', 'note', 'due_date', 'priority', 'finished', 'tags', 'subtasks' );
	if ( ! in_array( $field, $allowed, true ) ) {
		weekplan_ajax_reply( new WP_Error( 'weekplan_bad_field', '不认识的字段。' ) );
	}

	// 笔记是 Markdown 原文,不能过 sanitize_text_field(会吃掉换行)
	$raw = isset( $_POST['value'] ) ? wp_unslash( $_POST['value'] ) : '';

	switch ( $field ) {
		case 'note':
			$value = (string) $raw;
			break;
		case 'tags':
			$value = array_filter( array_map( 'trim', explode( "\n", (string) $raw ) ) );
			break;
		case 'subtasks':
			$decoded = json_decode( (string) $raw, true );
			$value   = is_array( $decoded ) ? $decoded : array();
			break;
		case 'finished':
			$value = ( '1' === (string) $raw || 'true' === (string) $raw );
			break;
		case 'priority':
			$value = (int) $raw;
			break;
		default:
			$value = sanitize_text_field( (string) $raw );
	}

	weekplan_ajax_reply( weekplan_update_todo( $id, array( $field => $value ) ) );
}

function weekplan_ajax_delete(): void {
	weekplan_ajax_guard();

	$id = weekplan_post_int( 'todo_id' );
	if ( ! weekplan_delete_todo( $id ) ) {
		weekplan_ajax_reply( new WP_Error( 'weekplan_delete_failed', '删除失败。' ) );
	}
	weekplan_ajax_reply( array() );
}

/* ---------- 标签管理 ---------- */

function weekplan_ajax_tag_save(): void {
	weekplan_ajax_guard();

	$result = weekplan_save_tag(
		weekplan_post_int( 'term_id' ),
		weekplan_post_text( 'name' ),
		weekplan_post_text( 'color' )
	);
	weekplan_ajax_reply( $result );
}

function weekplan_ajax_tag_delete(): void {
	weekplan_ajax_guard();

	if ( ! weekplan_delete_tag( weekplan_post_int( 'term_id' ) ) ) {
		weekplan_ajax_reply( new WP_Error( 'weekplan_tag_delete_failed', '删除失败。' ) );
	}
	weekplan_ajax_reply( array() );
}

function weekplan_ajax_batch(): void {
	weekplan_ajax_guard();

	$raw = isset( $_POST['weekdays'] ) ? (array) wp_unslash( $_POST['weekdays'] ) : array();

	weekplan_ajax_reply(
		weekplan_batch_schedule(
			weekplan_post_int( 'todo_id' ),
			weekplan_post_text( 'from' ),
			weekplan_post_text( 'to' ),
			$raw
		)
	);
}

function weekplan_ajax_shift(): void {
	weekplan_ajax_guard();

	weekplan_ajax_reply(
		weekplan_shift_todo( weekplan_post_int( 'todo_id' ), (int) weekplan_post_text( 'days' ) )
	);
}

function weekplan_ajax_preview(): void {
	weekplan_ajax_guard();

	$raw = isset( $_POST['value'] ) ? wp_unslash( $_POST['value'] ) : '';
	weekplan_ajax_reply( array( 'html' => weekplan_render_markdown( (string) $raw ) ) );
}

/**
 * 页面上会随数据变化的几块,按眼下看的那一周和标签筛选重新渲染。
 *
 * 前端每次写成功后取一次,整块换掉。一次改动会牵动哪些地方(改标题要动
 * 卡片,结项要把左栏那条收走,拖进某天要把它从「未来计划」挪进「待办」)
 * 不必逐个记着去补 —— 这里给的就是刷新整页后会看到的样子。
 *
 * todo_id 是详情栏正开着的那条:只回它的排期一览,详情栏里的输入框不动。
 */
function weekplan_ajax_view(): void {
	weekplan_ajax_guard();

	$day = weekplan_parse_date( weekplan_post_text( 'week' ) );
	if ( null === $day ) {
		weekplan_ajax_reply( new WP_Error( 'weekplan_bad_date', '日期格式不对。' ) );
	}

	$week_start = weekplan_week_start_of( $day );
	$active_tag = weekplan_valid_tag( weekplan_post_int( 'tag' ) );
	$view       = weekplan_view_data( $week_start, $active_tag );

	$days = array();
	foreach ( weekplan_week_days( $week_start ) as $item ) {
		$days[ $item['date'] ] = weekplan_capture( 'weekplan_render_cards', $view['schedule'][ $item['date'] ] ?? array() );
	}

	$reply = array(
		'overdue'           => weekplan_capture( 'weekplan_render_overdue', $view['overdue'] ),
		'tags'              => weekplan_capture( 'weekplan_render_tag_group', $week_start, $active_tag ),
		'scheduled'         => weekplan_capture( 'weekplan_render_sidebar_list', $view['sidebar']['scheduled'], WEEKPLAN_EMPTY_SCHEDULED ),
		'unscheduled'       => weekplan_capture( 'weekplan_render_sidebar_list', $view['sidebar']['unscheduled'], WEEKPLAN_EMPTY_UNSCHEDULED ),
		'unscheduled_count' => count( $view['sidebar']['unscheduled'] ),
		'days'              => $days,
	);

	$todo_id = weekplan_post_int( 'todo_id' );
	if ( $todo_id > 0 ) {
		$todo = weekplan_todo_summary( $todo_id );
		if ( null === $todo ) {
			// 详情栏开着的那条已经被删了,整个详情栏回到空状态
			$reply['detail_gone'] = weekplan_capture( 'weekplan_render_detail_empty' );
		} else {
			$reply['detail'] = weekplan_capture( 'weekplan_render_detail_schedule', $todo );
		}
	}

	weekplan_ajax_reply( $reply );
}

/* ---------- 便签 ---------- */

function weekplan_ajax_memo(): void {
	weekplan_ajax_guard();

	// 便签是 HTML,不能过 sanitize_text_field;白名单过滤在 weekplan_save_memo 里
	$raw = isset( $_POST['value'] ) ? wp_unslash( $_POST['value'] ) : '';
	weekplan_save_memo( (string) $raw );
	weekplan_ajax_reply( array() );
}
