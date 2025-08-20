import tkinter as tk
from tkinter import filedialog, messagebox
import chess
import chess.pgn
from io import StringIO

# --- Unicode pieces mapping ---
UNICODE_PIECES = {
    chess.Piece(chess.KING, chess.WHITE): "\u2654",
    chess.Piece(chess.QUEEN, chess.WHITE): "\u2655",
    chess.Piece(chess.ROOK, chess.WHITE): "\u2656",
    chess.Piece(chess.BISHOP, chess.WHITE): "\u2657",
    chess.Piece(chess.KNIGHT, chess.WHITE): "\u2658",
    chess.Piece(chess.PAWN, chess.WHITE): "\u2659",
    chess.Piece(chess.KING, chess.BLACK): "\u265A",
    chess.Piece(chess.QUEEN, chess.BLACK): "\u265B",
    chess.Piece(chess.ROOK, chess.BLACK): "\u265C",
    chess.Piece(chess.BISHOP, chess.BLACK): "\u265D",
    chess.Piece(chess.KNIGHT, chess.BLACK): "\u265E",
    chess.Piece(chess.PAWN, chess.BLACK): "\u265F",
}

LIGHT_COLOR = "#F0D9B5"
DARK_COLOR = "#B58863"
HIGHLIGHT_FROM = "#f6f669"
HIGHLIGHT_TO = "#a9d18e"
HIGHLIGHT_MOVE = "#88c0d0"
CHECK_COLOR = "#ff7070"

SQUARE_SIZE = 80
BOARD_SIZE = SQUARE_SIZE * 8
PIECE_FONT = ("Segoe UI Symbol", 44)  # supports chess Unicode on Windows; try Arial Unicode/DejaVu elsewhere

class PromotionDialog(tk.Toplevel):
    def __init__(self, parent, color):
        super().__init__(parent)
        self.title("Promote pawn")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()

        label = tk.Label(self, text="Choose promotion piece:")
        label.pack(padx=10, pady=(10, 0))

        frm = tk.Frame(self)
        frm.pack(padx=10, pady=10)

        # Order: Queen, Rook, Bishop, Knight
        for piece_type, name in [
            (chess.QUEEN, "Queen"),
            (chess.ROOK, "Rook"),
            (chess.BISHOP, "Bishop"),
            (chess.KNIGHT, "Knight"),
        ]:
            p = chess.Piece(piece_type, color)
            btn = tk.Button(
                frm,
                text=f"{UNICODE_PIECES[p]} {name}",
                width=12,
                command=lambda pt=piece_type: self._choose(pt),
                font=("Segoe UI Symbol", 16),
            )
            btn.pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_visibility()
        self.focus_set()

    def _choose(self, piece_type):
        self.result = piece_type
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Chess - Tkinter + python-chess")
        self.board = chess.Board()
        self.flipped = False  # if True, black at bottom
        self.selected_square = None
        self.legal_dests_for_selected = set()
        self.last_move = None

        # Layout: left board canvas, right sidebar
        container = tk.Frame(root)
        container.pack(padx=8, pady=8)

        self.canvas = tk.Canvas(container, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=6)

        # Move list
        tk.Label(container, text="Moves").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.move_list = tk.Listbox(container, width=28, height=22)
        self.move_list.grid(row=1, column=1, rowspan=1, sticky="n", padx=(10, 0))

        # Buttons
        self.btn_undo = tk.Button(container, text="Undo", command=self.undo)
        self.btn_undo.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))

        self.btn_reset = tk.Button(container, text="New Game", command=self.new_game)
        self.btn_reset.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(5, 0))

        self.btn_flip = tk.Button(container, text="Flip Board", command=self.flip_board)
        self.btn_flip.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=(5, 0))

        # PGN controls
        self.btn_save = tk.Button(container, text="Save PGN", command=self.save_pgn)
        self.btn_save.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=(5, 0))

        self.btn_load = tk.Button(container, text="Load PGN", command=self.load_pgn)
        self.btn_load.grid(row=6, column=1, sticky="ew", padx=(10, 0), pady=(5, 0))

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Configure>", self.on_resize)

        self.draw()

    # --- Utility coordinate conversion ---
    def square_at(self, x, y):
        size = min(self.canvas.winfo_width(), self.canvas.winfo_height())
        sq = size // 8
        file_idx = int(x // sq)
        rank_idx = 7 - int(y // sq)
        if self.flipped:
            file_idx = 7 - file_idx
            rank_idx = 7 - rank_idx
        if 0 <= file_idx < 8 and 0 <= rank_idx < 8:
            return chess.square(file_idx, rank_idx)
        return None

    def square_to_xy(self, square):
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        if self.flipped:
            file_idx = 7 - file_idx
            rank_idx = 7 - rank_idx
        size = min(self.canvas.winfo_width(), self.canvas.winfo_height())
        sq = size / 8
        x0 = file_idx * sq
        y0 = (7 - rank_idx) * sq
        x1 = x0 + sq
        y1 = y0 + sq
        return x0, y0, x1, y1

    # --- Drawing ---
    def draw_board(self):
        self.canvas.delete("square")
        size = min(self.canvas.winfo_width(), self.canvas.winfo_height())
        sq = size / 8
        for r in range(8):
            for f in range(8):
                if self.flipped:
                    df = 7 - f
                    dr = 7 - r
                else:
                    df, dr = f, r
                x0 = df * sq
                y0 = r * sq
                x1 = x0 + sq
                y1 = y0 + sq
                color = LIGHT_COLOR if (df + (7 - r)) % 2 == 0 else DARK_COLOR
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, width=0, tags=("square",))

        # File/rank labels
        self.canvas.delete("labels")
        files = "abcdefgh"
        ranks = "12345678"
        for f in range(8):
            file_label = files[f] if not self.flipped else files[7 - f]
            self.canvas.create_text(
                (f + 0.05) * sq, 8 * sq - 5, anchor="sw", text=file_label, tags=("labels",)
            )
        for r in range(8):
            rank_label = ranks[r] if self.flipped else ranks[7 - r]
            self.canvas.create_text(
                5, (r + 0.95) * sq, anchor="sw", text=rank_label, tags=("labels",)
            )

    def highlight(self):
        # Remove old highlights
        self.canvas.delete("highlight")
        # Last move highlight
        if self.last_move is not None:
            for sq in [self.last_move.from_square, self.last_move.to_square]:
                x0, y0, x1, y1 = self.square_to_xy(sq)
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=HIGHLIGHT_MOVE, width=4, tags=("highlight",))
        # Selected square
        if self.selected_square is not None:
            x0, y0, x1, y1 = self.square_to_xy(self.selected_square)
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=HIGHLIGHT_FROM, width=4, tags=("highlight",))
            # Destinations
            for dest in self.legal_dests_for_selected:
                x0, y0, x1, y1 = self.square_to_xy(dest)
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=HIGHLIGHT_TO, width=3, tags=("highlight",))
        # Check highlight
        if self.board.is_check():
            king_sq = self.board.king(self.board.turn)
            if king_sq is not None:
                x0, y0, x1, y1 = self.square_to_xy(king_sq)
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=CHECK_COLOR, width=4, tags=("highlight",))

    def draw_pieces(self):
        self.canvas.delete("piece")
        size = min(self.canvas.winfo_width(), self.canvas.winfo_height())
        sq = size / 8
        for square, piece in self.board.piece_map().items():
            x0, y0, x1, y1 = self.square_to_xy(square)
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            self.canvas.create_text(
                cx, cy, text=UNICODE_PIECES[piece], font=PIECE_FONT, tags=("piece",)
            )

    def draw(self):
        self.draw_board()
        self.highlight()
        self.draw_pieces()
        self.refresh_move_list()

    # --- Events ---
    def on_click(self, event):
        square = self.square_at(event.x, event.y)
        if square is None:
            return
        elif self.selected_square is None:
            piece = self.board.piece_at(square)
            if piece is None or piece.color != self.board.turn:
                return
            self.selected_square = square
            # Gather legal moves from this square
            self.legal_dests_for_selected = {m.to_square for m in self.board.legal_moves if m.from_square == square}
            self.draw()
        else:
            if square == self.selected_square:
                # Deselect
                self.selected_square = None
                self.legal_dests_for_selected = set()
                self.draw()
                return
            # Attempt move
            move = chess.Move(self.selected_square, square)
            if move not in self.board.legal_moves:
                # Handle promotion if necessary
                if self._is_promotion_attempt(self.selected_square, square):
                    promo_type = self.ask_promotion(self.board.turn)
                    if promo_type is None:
                        # cancelled
                        self.selected_square = None
                        self.legal_dests_for_selected = set()
                        self.draw()
                        return
                    move = chess.Move(self.selected_square, square, promotion=promo_type)
                else:
                    # Illegal -> select new if it's your piece
                    piece = self.board.piece_at(square)
                    if piece and piece.color == self.board.turn:
                        self.selected_square = square
                        self.legal_dests_for_selected = {m.to_square for m in self.board.legal_moves if m.from_square == square}
                        self.draw()
                        return
                    # otherwise ignore
            if move in self.board.legal_moves:
                self.board.push(move)
                self.last_move = move
            self.selected_square = None
            self.legal_dests_for_selected = set()
            self.draw()
            if self.board.is_game_over():
                print("game over")

    def _is_promotion_attempt(self, from_sq, to_sq):
        piece = self.board.piece_at(from_sq)
        if not piece or piece.piece_type != chess.PAWN:
            return False
        rank = chess.square_rank(to_sq)
        return (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0)

    def ask_promotion(self, color):
        dlg = PromotionDialog(self.root, color)
        return dlg.result

    def on_resize(self, event):
        # Keep canvas square
        size = min(event.width, event.height)
        self.canvas.config(width=size, height=size)
        self.draw()

    # --- Controls ---
    def undo(self):
        if len(self.board.move_stack) > 0:
            self.board.pop()
            self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
            self.draw()

    def new_game(self):
        if len(self.board.move_stack) > 0:
            if not messagebox.askyesno("New Game", "Start a new game and discard current moves?"):
                return
        self.board.reset()
        self.last_move = None
        self.selected_square = None
        self.legal_dests_for_selected = set()
        self.move_list.delete(0, tk.END)
        self.draw()

    def flip_board(self):
        self.flipped = not self.flipped
        self.draw()

    def refresh_move_list(self):
        # Rebuild SAN list from scratch
        self.move_list.delete(0, tk.END)
        tmp_board = chess.Board()
        ply = 1
        for mv in self.board.move_stack:
            san = tmp_board.san(mv)
            if tmp_board.turn == chess.WHITE:
                self.move_list.insert(tk.END, f"{ply}. {san}")
            else:
                last = self.move_list.get(tk.END)
                self.move_list.delete(tk.END)
                self.move_list.insert(tk.END, f"{last} {san}")
                ply += 1
            tmp_board.push(mv)
        # Autoscroll to end
        self.move_list.see(tk.END)

    def save_pgn(self):
        if len(self.board.move_stack) == 0:
            messagebox.showinfo("Save PGN", "No moves to save.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".pgn", filetypes=[("PGN files", ".pgn"), ("All files", "*.*")]
        )
        if not filename:
            return
        game = chess.pgn.Game.from_board(self.board)
        with open(filename, "w", encoding="utf-8") as f:
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            f.write(game.accept(exporter))
        messagebox.showinfo("Save PGN", f"Saved to {filename}")

    def load_pgn(self):
        filename = filedialog.askopenfilename(filetypes=[("PGN files", ".pgn"), ("All files", "*.*")])
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                game = chess.pgn.read_game(f)
            if game is None:
                raise ValueError("No game found in PGN.")
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            self.board = board
            self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
            self.selected_square = None
            self.legal_dests_for_selected = set()
            self.draw()
        except Exception as e:
            messagebox.showerror("Load PGN", f"Failed to load PGN: {e}")


def main():
    root = tk.Tk()
    app = ChessGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
