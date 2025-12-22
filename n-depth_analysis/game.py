import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import chess
import chess.pgn
import chess.engine
from io import StringIO
import copy

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

STARTING_BOARD = [
    [chess.Piece.from_symbol("R"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("r")],				
    [chess.Piece.from_symbol("N"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("n")],				
    [chess.Piece.from_symbol("B"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("b")],				
    [chess.Piece.from_symbol("Q"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("q")],				
    [chess.Piece.from_symbol("K"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("k")],				
    [chess.Piece.from_symbol("B"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("b")],				
    [chess.Piece.from_symbol("N"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("n")],				
    [chess.Piece.from_symbol("R"), chess.Piece.from_symbol("P"), None, None, None, None, chess.Piece.from_symbol("p"), chess.Piece.from_symbol("r")]				
    ]


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

class SetUpPosition(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Position Set-Up"
        self.resizable(False, False)
        self.transient(parent)
        self.chessBoard = copy.deepcopy(STARTING_BOARD)
        self.selectedPiece = None
        self.currentMoveColor = None
        self.flipped = False  # if True, black at bottom
        self.whiteShortCastle = None
        self.whiteLongCastle = None
        self.blackShortCastle = None
        self.blackLongCastle = None
        self.whiteKingPosition = (4, 0)
        self.blackKingPosition = (4, 7)
        self.result = None
        self.grab_set()
        self.entered = True
        self.chosenPiece = None
        self.chosenPieceSquare = None
        
        label = tk.Label(self, text="Choose piece:")
        label.pack(padx=10, pady=(10, 0))

        container = tk.Frame(self)
        container.pack()


        self.canvas = tk.Canvas(container, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=12)

        self.buttonFrame = tk.Frame(container)
        self.buttonFrame.grid(row=1, column=1,rowspan=5)


        self.btn_reset = tk.Button(self.buttonFrame, text="Reset Board", command=self.reset_board)
        self.btn_reset.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_clear = tk.Button(self.buttonFrame, text="Clear Board", command=self.clear_board)
        self.btn_clear.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_flip = tk.Button(self.buttonFrame, text="Flip Board", command=self.flip_board)
        self.btn_flip.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.is_white_turn = tk.Radiobutton(self.buttonFrame, text="White's move", variable=self.currentMoveColor, value=chess.WHITE, command=lambda : self._changeCurrentColor(chess.WHITE))
        self.is_white_turn.pack(side="top", fill=tk.BOTH, padx=5, pady=10)

        self.is_black_turn = tk.Radiobutton(self.buttonFrame, text="Black's move", variable=self.currentMoveColor, value=chess.BLACK, command=lambda : self._changeCurrentColor(chess.BLACK))
        self.is_black_turn.pack(side="top", fill=tk.BOTH, padx=5, pady=10)

        self.castlesFrame = tk.Frame(container)
        self.castlesFrame.grid(row = 5, column=1, rowspan=4)

        self.white_short_castle = tk.Checkbutton(self.castlesFrame, text="White Short Castle", variable=self.whiteShortCastle, onvalue=True, offvalue = False)
        self.white_short_castle.pack(side="top", fill=tk.BOTH, padx=5, pady=10)

        self.white_long_castle = tk.Checkbutton(self.castlesFrame, text="White Long Castle", variable=self.whiteLongCastle, onvalue=True, offvalue = False)
        self.white_long_castle.pack(side="top", fill=tk.BOTH, padx=5, pady=10)

        self.black_short_castle = tk.Checkbutton(self.castlesFrame, text="Black Short Castle", variable=self.blackShortCastle, onvalue=True, offvalue = False)
        self.black_short_castle.pack(side="top", fill=tk.BOTH, padx=5, pady=10)

        self.black_long_castle = tk.Checkbutton(self.castlesFrame, text="Black Long Castle", variable=self.blackLongCastle, onvalue=True, offvalue = False)
        self.black_long_castle.pack(side="top", fill=tk.BOTH, padx=5, pady=10)


        self.print_fen = tk.Button(container, text="Load FEN", command=self.generate_fen)
        self.print_fen.grid(row=9, column = 1, rowspan=1)

        self.pieceFrame = tk.Frame(container)
        self.pieceFrame.grid(row = 12, column=0)

        
        self.currentMoveColor = chess.WHITE
        self.is_white_turn.invoke()

        self.white_short_castle.select()
        self.whiteShortCastle=True
        
        self.white_long_castle.select()
        self.whiteLongCastle=True
        
        self.black_short_castle.select()
        self.blackShortCastle=True

        self.black_long_castle.select()
        self.blackLongCastle=True

        row_count = 0
        # Order: Queen, Rook, Bishop, Knight
        for piece_color in [chess.WHITE, chess.BLACK]:
            tempFrame = tk.Frame(self.pieceFrame)
            tempFrame.grid(row = row_count, column = 0)
            
            for piece_type, name in [
                (chess.KING, "King"),
                (chess.QUEEN, "Queen"),
                (chess.ROOK, "Rook"),
                (chess.BISHOP, "Bishop"),
                (chess.KNIGHT, "Knight"),
                (chess.PAWN, "Pawn")
            ]:
                p = chess.Piece(piece_type, piece_color)
                btn = tk.Radiobutton(
                    tempFrame,
                    text=f"{UNICODE_PIECES[p]}",
                    font=PIECE_FONT,
                    variable = self.selectedPiece,
                    value = p,
                    indicatoron=0
                )
                todo = lambda button=btn, val=p: self._choose(button, val)
                btn.configure(command = todo)
                btn.pack(side="right")
                
            row_count += 1
            

        
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_visibility()
        self.focus_set()
        

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.delete_piece)
        
        self.draw()

    def _choose(self, button, piece):

        
        if self.selectedPiece == piece:
            button.deselect()
            self.selectedPiece = None
        else:
            self.selectedPiece = piece

    def _cancel(self):
        self.selectedPiece = None
        self.entered = False
        self.destroy()

    def _changeCurrentColor(self, color):
        self.currentMoveColor = color

    def generate_fen(self):
        fen_string = ""
        for x in range(len(self.chessBoard)):
            empty_square_counter = 0
            for y in range(len(self.chessBoard[x])):
                square = self.chessBoard[y][7-x]
                if square != None:
                    if empty_square_counter > 0:
                        fen_string += str(empty_square_counter)
                        empty_square_counter = 0
                    fen_string += square.symbol()
                else:
                    empty_square_counter += 1
            if empty_square_counter > 0:
                fen_string += str(empty_square_counter)
            if x != len(self.chessBoard) - 1:
                fen_string += r"/"

        if self.currentMoveColor == chess.WHITE:
            fen_string += " w "
        else:
            fen_string += " b "


        if self.whiteShortCastle:
            fen_string += "K"
        if self.whiteLongCastle:
            fen_string += "Q"
        if self.blackShortCastle:
            fen_string += "k"
        if self.blackLongCastle:
            fen_string += "q"
        if not(self.whiteShortCastle and self.whiteLongCastle and self.blackShortCastle and self.blackLongCastle):
            fen_string += "-"
        fen_string += " - 0 1"
        
        self.result = fen_string
        self.entered = False
        self.destroy()

    def delete_piece(self, event):
        file_idx, rank_idx = self.square_at(event.x, event.y)
        original_piece = self.chessBoard[file_idx][rank_idx]
        self.chessBoard[file_idx][rank_idx] = None
        self.draw()

    def reset_board(self):
        self.chessBoard = copy.deepcopy(STARTING_BOARD)
        self.draw()

    def clear_board(self):
        self.chessBoard = [[None for x in range(8)] for y in range(8)]
        self.draw()

    def flip_board(self):
        self.flipped = not self.flipped
        self.draw()

    def draw(self):
        self.draw_board()
        self.highlight()
        self.draw_pieces()

    def highlight(self):
        # Remove old highlights
        self.canvas.delete("highlight")
        # Selected square
        if self.chosenPieceSquare != None:
            x0, y0, x1, y1 = self.square_to_xy(self.chosenPieceSquare)
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=HIGHLIGHT_MOVE, width=4, tags=("highlight",))


    def on_click(self, event):
        
        file_idx, rank_idx = self.square_at(event.x, event.y)
        
        piece = self.chessBoard[file_idx][rank_idx]

        if self.selectedPiece != None:
            if self.selectedPiece == chess.Piece.from_symbol("K"):
                self.chessBoard[self.whiteKingPosition[0]][self.whiteKingPosition[1]] = None
                self.whiteKingPosition = (file_idx, rank_idx)
            elif self.selectedPiece == chess.Piece.from_symbol("k"):
                self.chessBoard[self.blackKingPosition[0]][self.blackKingPosition[1]] = None
                self.blackKingPosition = (file_idx, rank_idx)
            self.chessBoard[file_idx][rank_idx] = self.selectedPiece
        else:
            if self.chosenPiece == None:
                self.chosenPiece = piece
                self.chosenPieceSquare = self.square_at(event.x, event.y)
                self.draw()
                return
            else:
                chosenPieceRank = self.chosenPieceSquare[1]
                chosenPieceFile = self.chosenPieceSquare[0]
                self.chessBoard[file_idx][rank_idx] = self.chosenPiece
                self.chessBoard[chosenPieceFile][chosenPieceRank] = None
                self.chosenPiece = None
                self.chosenPieceSquare = None
        
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
            return (file_idx, rank_idx)
        return None

    def square_to_xy(self, square):
        file_idx = square[0]
        rank_idx = square[1]
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

    def draw_pieces(self):
        self.canvas.delete("piece")
        size = min(self.canvas.winfo_width(), self.canvas.winfo_height())
        sq = size / 8
        for x in range(len(self.chessBoard)):
            for y in range(len(self.chessBoard[x])):
                square_piece = self.chessBoard[x][y]
                if self.chessBoard[x][y] != None:
                    x0, y0, x1, y1 = self.square_to_xy((x,y))
                    cx = (x0 + x1) / 2
                    cy = (y0 + y1) / 2
                    self.canvas.create_text(
                        cx, cy, text=UNICODE_PIECES[self.chessBoard[x][y]], font=PIECE_FONT, tags=("piece",)
                    )

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
                color = DARK_COLOR if (df + (7 - r)) % 2 == 0 else LIGHT_COLOR
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



class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Chess - Tkinter + python-chess")
        self.board = chess.Board()
        self.flipped = False  # if True, black at bottom
        self.selected_square = None
        self.legal_dests_for_selected = set()
        self.last_move = None
        self.engine = chess.engine.SimpleEngine.popen_uci("../stockfish/stockfish-windows-x86-64-avx2.exe")
        self.current_analysis = None
        self.fen_used = False
        self.fen_string = None
        self.analysis_boxes = []

        # Layout: left board canvas, right sidebar
        container = tk.Frame(root)
        container.pack(padx=8, pady=8, anchor='w')

        self.canvas = tk.Canvas(container, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=6, sticky="s")

        # Move list
        tk.Label(container, text="Moves").grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.move_list = tk.Listbox(container, width=28, height=22)
        self.move_list.grid(row=1, column=2, rowspan=1, sticky="n", padx=(10, 0))

        # Position Analysis
        tk.Label(container, text="Analysis").grid(row=6, column=0, sticky="w")
        self.analysis_holder = tk.Frame(container)
        self.analysis_holder.grid(row=8, column=0, sticky='w')
        tk.Label(self.analysis_holder, text="1st").grid(row=0,column=0)
        tk.Label(self.analysis_holder, text="2nd").grid(row=0,column=1)
        tk.Label(self.analysis_holder, text="3rd").grid(row=0,column=2)

        for i in range(3):
            temp_analysis_box = tk.Listbox(self.analysis_holder)
            temp_analysis_box.grid(row=1, column=i, sticky='w')
            self.analysis_boxes.append(temp_analysis_box)

        self.buttonFrame = tk.Frame(container)
        self.buttonFrame.grid(row=2, column=2)
        

        # Buttons
        self.btn_undo = tk.Button(self.buttonFrame, text="Undo", command=self.undo)
        self.btn_undo.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_reset = tk.Button(self.buttonFrame, text="New Game", command=self.new_game)
        self.btn_reset.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_flip = tk.Button(self.buttonFrame, text="Flip Board", command=self.flip_board)
        self.btn_flip.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        # PGN controls
        self.btn_save = tk.Button(self.buttonFrame, text="Save PGN", command=self.save_pgn)
        self.btn_save.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_load = tk.Button(self.buttonFrame, text="Load PGN", command=self.load_pgn)
        self.btn_load.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_save_fen = tk.Button(self.buttonFrame, text="Save FEN", command=self.save_fen)
        self.btn_save_fen.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_enter_fen = tk.Button(self.buttonFrame, text="Enter FEN", command=self.enter_fen)
        self.btn_enter_fen.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_analyse = tk.Button(self.buttonFrame, text="Analyse Position", command=self.analyse_position)
        self.btn_analyse.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

        self.btn_set_up = tk.Button(self.buttonFrame, text="Set-Up Position", command=self.set_up)
        self.btn_set_up.pack(side="top", fill=tk.BOTH, padx=5, pady=5)

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
                color = DARK_COLOR if (df + (7 - r)) % 2 == 0 else LIGHT_COLOR
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
        #.analyse_position()

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
        self.selected_square = None
        self.legal_dests_for_selected = set()
        if len(self.board.move_stack) > 0:
            self.board.pop()
            self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
            self.draw()

    def new_game(self):
        if len(self.board.move_stack) > 0:
            if not messagebox.askyesno("New Game", "Start a new game and discard current moves?"):
                return
        self.board.reset()
        self.fen_used = False
        self.fen_string = None
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
        if self.fen_used:  
            tmp_board.set_fen(self.fen_string)
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

    def save_fen(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".fen", filetypes=[("FEN files", ".fen"), ("All files", "*.*")]
        )
        if not filename:
            return
        fen_string = self.board.fen()
        print(fen_string)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(fen_string)
        messagebox.showinfo("Save FEN", f"Saved to {filename}")


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
            self.fen_used = False
            self.fen_string = None
            self.board = board
            self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
            self.selected_square = None
            self.legal_dests_for_selected = set()
            self.draw()
        except Exception as e:
            messagebox.showerror("Load PGN", f"Failed to load PGN: {e}")

    def enter_fen(self):
        fen_input = simpledialog.askstring(title="Input FEN",
                                  prompt="Enter FEN string:")
        
        if not fen_input:
            return
        try:
            self.fen_used = True
            self.fen_string = fen_input
            self.board = chess.Board()
            self.board.set_fen(self.fen_string)
            self.last_move = None
            self.selected_square = None
            self.legal_dests_for_selected = set()
            self.move_list.delete(0, tk.END)
            self.draw()
        except Exception as e:
            messagebox.showerror("Load FEN", f"Failed to load FEN: {e}")


    def analyse_position(self):
        self.current_analysis = []
        for listbox in self.analysis_holder.winfo_children():
            for item in listbox.winfo_children():
                item.destroy()
        for i in range(1,11):
            info = self.engine.analyse(self.board, chess.engine.Limit(depth=2*i),multipv=3)
            turn = "White" if info[0]['score'].turn else "Black"
            temp_analysis = []
            for inf in info:
                temp_analysis.append((i, turn, inf['pv'][0].uci(), inf['score']))
            self.current_analysis.append(temp_analysis)
            col = 0
            for dep in self.current_analysis[-1]:
                current_analysis_box = self.analysis_boxes[col]
                stext = tk.Label(current_analysis_box, text=f"{dep[0]*2} - {dep[1]}: {dep[2]} - {dep[3].pov(chess.WHITE)}")
                todo = lambda event, inf = info[col]: self._print_analysis(inf)
                stext.bind("<Button-1>", todo)
                stext.pack()
                col += 1
                current_analysis_box.see(tk.END)
            

    def _print_analysis(self, info):
        infoMessage = ''
        infoMessage += f"PV: {info['multipv']}\n"
        infoMessage += f"Depth: {info['depth']}\n"
        infoMessage += f"Score: {info['score'].pov(chess.WHITE)}\n\n"
        infoMessage += f"Moves: "
        infoMessage += ', '.join([x.uci() for x in info['pv']])
        infoMessage += "\n"
        messagebox.Message(message=infoMessage).show()

    def set_up(self):
        if len(self.board.move_stack) > 0:
            if not messagebox.askyesno("Set-Up Position", "Start a new game and set-up position?"):
                return

        fen = SetUpPosition(self.root)
        self.root.wait_window(fen)

        
        if fen.result != None:
            self.fen_used = True
            self.fen_string = fen.result
            self.board = chess.Board()
            self.board.set_fen(self.fen_string)
            self.last_move = None
            self.selected_square = None
            self.legal_dests_for_selected = set()
            self.move_list.delete(0, tk.END)
            self.draw()
        


def main():
    root = tk.Tk()
    app = ChessGUI(root)
    root.mainloop()
    app.engine.quit()

if __name__ == "__main__":
    main()
