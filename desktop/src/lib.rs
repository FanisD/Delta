use serde::Serialize;
use std::{
    env,
    net::TcpListener,
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager, RunEvent,
};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};

const DEFAULT_PORT: u16 = 18_735;

#[derive(Default)]
struct SidecarState(Arc<Mutex<Option<Child>>>);

#[derive(Clone, Serialize)]
struct StartupFailure {
    message: String,
}

fn free_port(preferred: u16) -> std::io::Result<u16> {
    if preferred != 0 && TcpListener::bind(("127.0.0.1", preferred)).is_ok() {
        return Ok(preferred);
    }
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    Ok(listener.local_addr()?.port())
}

fn sidecar_path(resource_dir: Option<&Path>) -> PathBuf {
    let filename = if cfg!(target_os = "windows") { "delta-backend.exe" } else { "delta-backend" };
    if let Some(dir) = resource_dir {
        let binaries = dir.join("binaries");
        let direct = binaries.join(filename);
        if direct.exists() { return direct; }
        if let Ok(entries) = std::fs::read_dir(&binaries) {
            if let Some(found) = entries.flatten().map(|entry| entry.path()).find(|path| {
                path.file_name().and_then(|name| name.to_str()).is_some_and(|name| name.starts_with("delta-backend"))
            }) { return found; }
        }
        return direct;
    }
    PathBuf::from("binaries").join(filename)
}

fn start_sidecar(app: &AppHandle, port: u16, state: &SidecarState) -> Result<(), String> {
    let path = sidecar_path(app.path().resource_dir().ok().as_deref());
    if !path.exists() {
        return Err(format!("Backend sidecar is missing: {}", path.display()));
    }
    let child = Command::new(path)
        .arg("--no-browser")
        .env("APP_PORT", port.to_string())
        .env("APP_NO_BROWSER", "1")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("Could not start backend sidecar: {error}"))?;
    *state.0.lock().map_err(|_| "sidecar state lock poisoned".to_string())? = Some(child);
    Ok(())
}

fn stop_sidecar(state: &SidecarState) {
    if let Ok(mut guard) = state.0.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            for _ in 0..20 {
                if child.try_wait().ok().flatten().is_some() {
                    return;
                }
                thread::sleep(Duration::from_millis(25));
            }
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn sidecar_exited(state: &SidecarState) -> bool {
    state.0.lock().ok().and_then(|mut child| {
        child.as_mut().map(|process| process.try_wait().ok().flatten().is_some())
    }).unwrap_or(true)
}

fn show_startup_failure(app: &AppHandle, state: &SidecarState, message: String) {
    let handle = app.clone();
    let state = state.0.clone();
    let retry_state = SidecarState(state);
    app.dialog()
        .message(&message)
        .title("Delta could not start")
        .kind(MessageDialogKind::Error)
        .buttons(MessageDialogButtons::OkCancel)
        .show(move |retry| {
            if retry {
                let port = free_port(DEFAULT_PORT).unwrap_or(DEFAULT_PORT);
                if start_sidecar(&handle, port, &retry_state).is_ok() {
                    poll_health(&handle, port, &retry_state);
                } else {
                    show_startup_failure(&handle, &retry_state, "Retrying the Delta backend failed.".into());
                }
            }
        });
}

fn poll_health(app: &AppHandle, port: u16, state: &SidecarState) {
    let handle = app.clone();
    let state = state.0.clone();
    thread::spawn(move || {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_millis(750))
            .build();
        let url = format!("http://127.0.0.1:{port}/api/health");
        let deadline = std::time::Instant::now() + Duration::from_secs(30);
        while std::time::Instant::now() < deadline {
            if sidecar_exited(&SidecarState(state.clone())) {
                show_startup_failure(&handle, &SidecarState(state.clone()), "The Delta backend exited during startup.".into());
                return;
            }
            if let Ok(client) = &client {
                if client.get(&url).send().is_ok() {
                    if let Some(window) = handle.get_webview_window("main") {
                        let _ = window.navigate(url::Url::parse(&format!("http://127.0.0.1:{port}/")).unwrap());
                    }
                    let monitor_handle = handle.clone();
                    let monitor_state = state.clone();
                    thread::spawn(move || {
                        loop {
                            thread::sleep(Duration::from_secs(1));
                            if sidecar_exited(&SidecarState(monitor_state.clone())) {
                                let _ = monitor_handle.emit("delta://startup-failed", StartupFailure {
                                    message: "The Delta backend stopped unexpectedly.".into(),
                                });
                                show_startup_failure(
                                    &monitor_handle,
                                    &SidecarState(monitor_state.clone()),
                                    "The Delta backend stopped unexpectedly.".into(),
                                );
                                break;
                            }
                        }
                    });
                    return;
                }
            }
            thread::sleep(Duration::from_millis(200));
        }
        let message = "The Delta backend did not become ready. Check the desktop troubleshooting guide.".to_string();
        let _ = handle.emit("delta://startup-failed", StartupFailure { message: message.clone() });
        show_startup_failure(&handle, &SidecarState(state), message);
    });
}

#[tauri::command]
fn save_export_file(path: String, contents: Vec<u8>) -> Result<(), String> {
    std::fs::write(path, contents).map_err(|error| error.to_string())
}

#[tauri::command]
fn retry_startup(app: AppHandle, state: tauri::State<'_, SidecarState>) -> Result<(), String> {
    let port = free_port(DEFAULT_PORT).map_err(|error| error.to_string())?;
    start_sidecar(&app, port, &state)?;
    poll_health(&app, port, &state);
    Ok(())
}

fn menu(app: &AppHandle) -> tauri::Result<Menu<tauri::Wry>> {
    let quit = MenuItem::with_id(app, "quit", "Quit Delta", true, None::<&str>)?;
    let updates = MenuItem::with_id(app, "updates", "Check for Updates", true, None::<&str>)?;
    let about = MenuItem::with_id(app, "about", "About Delta", true, None::<&str>)?;
    let edit = Submenu::with_items(
        app,
        "Edit",
        true,
        &[&PredefinedMenuItem::undo(app, None)?, &PredefinedMenuItem::redo(app, None)?,
          &PredefinedMenuItem::separator(app)?, &PredefinedMenuItem::cut(app, None)?,
          &PredefinedMenuItem::copy(app, None)?, &PredefinedMenuItem::paste(app, None)?],
    )?;
    Menu::with_items(app, &[&edit, &updates, &about, &quit])
}

pub fn run() {
    let state = SidecarState::default();
    tauri::Builder::default()
        .manage(state)
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            let port = free_port(env::var("DELTA_PORT").ok().and_then(|v| v.parse().ok()).unwrap_or(DEFAULT_PORT))
                .map_err(|e| tauri::Error::Setup(format!("No free localhost port: {e}")))?;
            let state = app.state::<SidecarState>();
            start_sidecar(app.handle(), port, &state).map_err(tauri::Error::Setup)?;
            let window = app.get_webview_window("main")
                .ok_or_else(|| tauri::Error::Setup("main window was not created".into()))?;
            let _ = window.show(); // The about:blank page acts as the native splash.
            poll_health(app.handle(), port, &state);
            let show = MenuItem::with_id(app, "show", "Show Delta", true, None::<&str>)?;
            let hide = MenuItem::with_id(app, "hide", "Hide to Tray", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit-tray", "Quit", true, None::<&str>)?;
            let tray_menu = Menu::with_items(app, &[&show, &hide, &quit])?;
            TrayIconBuilder::new().menu(&tray_menu).tooltip("Delta").on_menu_event(|app, event| {
                match event.id().as_ref() {
                    "quit-tray" => app.exit(0),
                    "show" => if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); },
                    "hide" => if let Some(window) = app.get_webview_window("main") { let _ = window.hide(); },
                    _ => {}
                }
            }).build(app)?;
            Ok(())
        })
        .menu(|app| menu(app))
        .on_menu_event(|app, event| {
            if event.id().as_ref() == "quit" { app.exit(0); }
        })
        .invoke_handler(tauri::generate_handler![save_export_file, retry_startup])
        .build(tauri::generate_context!())
        .expect("error while building Delta desktop app")
        .run(|app, event| {
            if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
                stop_sidecar(&app.state::<SidecarState>());
            }
        });
}

#[cfg(test)]
mod tests {
    use super::free_port;
    use std::net::TcpListener;

    #[test]
    fn selects_a_bindable_ephemeral_port() {
        let port = free_port(0).expect("a local port should be available");
        let listener =
            TcpListener::bind(("127.0.0.1", port)).expect("selected port should be free");
        drop(listener);
    }
}
