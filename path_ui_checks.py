"""Actions-only real Tk/CustomTkinter path regression checks, also run frozen."""
import json
from pathlib import Path
import tempfile


def run_checks(gui, report_path, baseline=False):
    report = {"baseline": baseline, "checks": []}
    errors = []
    original_error = gui.messagebox.showerror
    original_dialog = gui.filedialog.askdirectory
    gui.messagebox.showerror = lambda *args, **kwargs: errors.append(args)
    root = gui.ctk.CTk()
    app = gui.PS5ContainerBuilderApp(root)
    report.update(tk_version=root.tk.call("info", "patchlevel"),
                  windowing_system=root.tk.call("tk", "windowingsystem"))
    assert report["windowing_system"] == "aqua", "These are native macOS tests"

    def prepare(entry, variable, value):
        variable.set(value)
        entry.focus_force()
        root.update()
        entry.select_clear()
        entry.icursor("end")
        root.update()

    def paste(entry, value, command=False):
        root.clipboard_clear()
        root.clipboard_append(value)
        root.update()
        entry._entry.event_generate("<Command-v>" if command else "<<Paste>>")
        root.update()

    try:
        root.update()
        fields = (("output", app.output_entry, app.output_var, "/Volumes/TAHOENTOSH - Data/PS5_OUTPUT"),
                  ("temp", app.temp_dir_entry, app.temp_dir_var, "/Volumes/TAHOENTOSH - Data/PS5_TEMP"))
        for name, entry, variable, path in fields:
            prepare(entry, variable, path)
            paste(entry, path)
            result = variable.get()
            if baseline:
                assert result == path + path, (name, result)
                report["checks"].append({"name": name + "_unselected_paste", "observed": result,
                                         "concatenation_reproduced": True})
            else:
                assert result == path, (name, result)
                report["checks"].append({"name": name + "_absolute_paste_replaces", "passed": True})
            prepare(entry, variable, path)
            entry._entry.event_generate("<Command-a>")
            root.update()
            selected = bool(entry.select_present())
            all_selected = selected and entry.index("sel.first") == 0 and entry.index("sel.last") == len(path)
            report["checks"].append({"name": name + "_cmd_a", "all_selected": all_selected})
            if not baseline:
                assert all_selected, name
            replacement = "/Volumes/Otra unidad/Salida ñ"
            paste(entry, replacement, command=True)
            report["checks"].append({"name": name + "_cmd_a_cmd_v", "observed": variable.get()})
            if not baseline:
                assert variable.get() == replacement
                prepare(entry, variable, path)
                paste(entry, path, command=True)
                assert variable.get() == path
                report["checks"].append({"name": name + "_cmd_v_no_selection", "passed": True})
                prepare(entry, variable, "/Volumes/Data/OLD")
                entry.select_range(len("/Volumes/Data/"), "end")
                paste(entry, "NEW")
                assert variable.get() == "/Volumes/Data/NEW"
                report["checks"].append({"name": name + "_fragment_selection", "passed": True})
                prepare(entry, variable, path)
                paste(entry, "")
                assert variable.get() == path
                report["checks"].append({"name": name + "_empty_clipboard", "passed": True})
                count = len(errors)
                paste(entry, path + path)
                assert variable.get() == path and len(errors) == count + 1
                report["checks"].append({"name": name + "_duplicate_paste_rejected", "passed": True})
                entry.configure(state="disabled")
                paste(entry, replacement)
                assert variable.get() == path
                entry.configure(state="normal")
                report["checks"].append({"name": name + "_disabled_paste", "passed": True})

        if not baseline:
            with tempfile.TemporaryDirectory(prefix="ps5-path-ui-") as tmp:
                chosen = Path(tmp) / "Salida ñ con espacios"
                chosen.mkdir()
                dialog_calls = []

                def choose(**kwargs):
                    dialog_calls.append(kwargs)
                    return str(chosen)

                gui.filedialog.askdirectory = choose
                for variable, button in ((app.output_var, app.browse_output_button),
                                         (app.temp_dir_var, app.browse_temp_button)):
                    variable.set("/missing/output/missing/output")
                    button.invoke()
                    assert variable.get() == str(chosen)
                    assert Path(dialog_calls[-1]["initialdir"]).is_dir()
                    gui.filedialog.askdirectory = lambda **kwargs: ""
                    button.invoke()
                    assert variable.get() == str(chosen)
                    gui.filedialog.askdirectory = choose
                report["checks"].append({"name": "browse_buttons_replace_and_cancel_preserves", "passed": True})
                file_path = chosen / "image.ffpfsc"
                file_path.touch()
                app.output_var.set(str(file_path))
                app.browse_output_button.invoke()
                assert dialog_calls[-1]["initialdir"] == str(chosen)
                report["checks"].append({"name": "browse_file_destination_uses_parent", "passed": True})
                for variable in (app.output_var, app.temp_dir_var):
                    app.output_var.set(str(chosen))
                    app.temp_dir_var.set(str(chosen))
                    variable.set("/Volumes/TAHOENTOSH - Data/PS5_OUTPUT" * 2)
                    count = len(errors)
                    app._on_action()
                    assert not app.is_running and app.worker_thread is None and len(errors) == count + 1
                report["checks"].append({"name": "concatenated_paths_block_worker", "passed": True})
                app.output_var.set(str(chosen))
                app.temp_dir_var.set(str(chosen / "missing"))
                count = len(errors)
                app._on_action()
                assert not app.is_running and app.worker_thread is None and len(errors) == count + 1
                report["checks"].append({"name": "missing_temp_blocks_worker", "passed": True})
                app.temp_dir_var.set(f'"{chosen}"')
                assert app._validated_path_fields() == (str(chosen), str(chosen))
                report["checks"].append({"name": "valid_quoted_temp_with_unicode", "passed": True})
        report["passed"] = True
        report["check_count"] = len(report["checks"])
        Path(report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    finally:
        app._on_close()
        gui.messagebox.showerror = original_error
        gui.filedialog.askdirectory = original_dialog
