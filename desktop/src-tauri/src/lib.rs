mod tray;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // 创建系统托盘
            tray::create_tray(app.handle())?;
            Ok(())
        })
        .on_window_event(|window, event| {
            // 点击关闭按钮时隐藏到托盘而非退出
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![open_video_window])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
async fn open_video_window(app: tauri::AppHandle) -> Result<(), String> {
    // 如果视频窗口已存在，聚焦它
    if let Some(window) = app.get_webview_window("video") {
        let _ = window.show();
        let _ = window.set_focus();
        return Ok(());
    }

    // 创建新的视频窗口
    tauri::WebviewWindowBuilder::new(&app, "video", tauri::WebviewUrl::App("/#/video".into()))
        .title("视频播放")
        .fullscreen(true)
        .resizable(true)
        .build()
        .map_err(|e| e.to_string())?;

    Ok(())
}
