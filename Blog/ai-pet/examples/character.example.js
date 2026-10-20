// AI 宠物的最小示例角色：一个方块脸。
// 用法：上传到 wp-content/uploads/ai-pet/character.js，刷新页面就能看到。
// 接口说明见 README「方式二：JS 角色文件」；在这个文件的基础上改，就能做出自己的角色。
(function () {
  const LINE = '#3a2f2a', FACE = '#f4c38a', CHEEK = '#f08a8a', WHITE = '#ffffff';

  window.AIPET_CHARACTER = {
    width: 32, height: 30,
    pixelated: true,
    rise: { up: -1, down: 3 },

    draw(ctx, s) {
      const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(x, y, w, h); };
      const r = s.rise;

      // 耳朵：s.ear 为 1、3 时右耳抬起一格
      const earLift = s.ear === 1 || s.ear === 3 ? 1 : 0;
      px(6, 1 + r, 5, 4, LINE); px(7, 2 + r, 3, 3, FACE);
      px(21, 1 + r - earLift, 5, 4, LINE); px(22, 2 + r - earLift, 3, 3, FACE);

      // 脸：描边 + 填充，下半截超出画布的部分自然被裁掉
      px(4, 4 + r, 24, 24, LINE);
      px(5, 5 + r, 22, 22, FACE);

      // 眼睛：s.look 让眼珠左右移一格
      const ex = s.look, ey = 12 + r;
      for (const x of [10 + ex, 19 + ex]) {
        if (s.blink || s.expr === 'sleepy') {
          px(x, ey + 1, 3, 1, LINE);
        } else if (s.expr === 'happy') {
          px(x, ey + 1, 1, 1, LINE); px(x + 1, ey, 1, 1, LINE); px(x + 2, ey + 1, 1, 1, LINE);
        } else if (s.expr === 'surprised') {
          px(x, ey - 1, 3, 3, LINE); px(x + 1, ey - 1, 1, 1, WHITE);
        } else {
          px(x, ey, 2, 3, LINE); px(x, ey, 1, 1, WHITE);
        }
      }

      // 害羞时脸红
      if (s.expr === 'shy') {
        px(7, 17 + r, 3, 1, CHEEK); px(22, 17 + r, 3, 1, CHEEK);
      }

      // 嘴：说话或惊讶时张开
      const my = 19 + r;
      if (s.talk || s.expr === 'surprised') {
        px(14, my, 4, 3, LINE);
      } else if (s.expr === 'happy') {
        px(13, my, 1, 1, LINE); px(14, my + 1, 4, 1, LINE); px(18, my, 1, 1, LINE);
      } else {
        px(15, my + 1, 2, 1, LINE);
      }

      // 两只前爪固定贴着底边，不随 rise 移动
      px(7, 26, 7, 4, LINE); px(8, 27, 5, 3, FACE);
      px(18, 26, 7, 4, LINE); px(19, 27, 5, 3, FACE);
    },

    lines: {
      home: [['欢迎来到「{site}」！我是{name}，点我可以聊天～', 'happy']],
      poke: [['哎呀！', 'surprised'], ['（方块脸变红了）', 'shy']],
    },
  };
})();
