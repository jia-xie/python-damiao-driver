#!/usr/bin/env python3
"""
Custom argparse formatter for colorized help text.
"""
import argparse
import re
import sys

from .display import RESET, BOLD, CYAN, BRIGHT_CYAN, GREEN, BLUE


class ColorizedHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter that adds colors to help text."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if stdout is a TTY to enable colors
        self._use_colors = sys.stdout.isatty()
    
    def _colorize(self, text: str, color: str) -> str:
        """Add color to text if colors are enabled."""
        if self._use_colors:
            return f"{color}{text}{RESET}"
        return text
    
    def _format_usage(self, usage, actions, groups, prefix):
        """Format usage with colors."""
        usage_text = super()._format_usage(usage, actions, groups, prefix)
        if self._use_colors:
            # Colorize the "usage:" prefix
            usage_text = usage_text.replace("usage: ", self._colorize("usage: ", BOLD))
        return usage_text
    
    def start_section(self, heading):
        """Start a section with colorized heading."""
        if self._use_colors:
            # Colorize section headings
            if heading in ["positional arguments", "options", "optional arguments", "Commands", "Commands:"]:
                heading = self._colorize(heading, BOLD + CYAN)
        super().start_section(heading)
    
    def _format_action_invocation(self, action):
        """Format action invocation (command/option name) with colors."""
        if not self._use_colors:
            return super()._format_action_invocation(action)
        
        # For subcommands, the action has choices dict - handle in _format_action
        if hasattr(action, 'choices') and isinstance(action.choices, dict):
            return super()._format_action_invocation(action)
        
        # For regular options, colorize them
        if hasattr(action, 'option_strings') and action.option_strings:
            parts = []
            for option_string in action.option_strings:
                parts.append(self._colorize(option_string, BLUE))
            return ', '.join(parts)
        
        return super()._format_action_invocation(action)
    
    def _format_action(self, action):
        """Format individual action with colors."""
        # Get the default formatting
        parts = super()._format_action(action)
        
        if not self._use_colors:
            return parts
        
        # Handle subparsers (subcommands)
        if hasattr(action, 'choices') and isinstance(action.choices, dict):
            # This is a subparsers action - format each subcommand
            for cmd_name, cmd_parser in action.choices.items():
                if cmd_name == 'gui':
                    # Highlight gui command name - match the pattern in help output
                    # Format: "    gui               Launch web-based GUI..."
                    pattern = r'(\s{4})(' + re.escape(cmd_name) + r')(\s+)'
                    replacement = r'\1' + self._colorize(r'\2', BRIGHT_CYAN + BOLD) + r'\3'
                    parts = re.sub(pattern, replacement, parts)
                    # Highlight (recommended) text
                    parts = parts.replace('(recommended)', self._colorize('(recommended)', GREEN + BOLD))
                else:
                    # Colorize other command names
                    pattern = r'(\s{4})(' + re.escape(cmd_name) + r')(\s+)'
                    replacement = r'\1' + self._colorize(r'\2', CYAN) + r'\3'
                    parts = re.sub(pattern, replacement, parts)
        
        # Options are already colored by _format_action_invocation, so skip here
        
        return parts
    
    def _format_text(self, text):
        """Format text with colors."""
        if not self._use_colors:
            return super()._format_text(text)
        
        # Colorize common patterns in epilog/description
        text = text.replace('COMMAND', self._colorize('COMMAND', BOLD))
        text = text.replace('damiao', self._colorize('damiao', BLUE + BOLD))
        # Be careful with gui replacement - only replace standalone word
        text = re.sub(r'\b(gui)\b', self._colorize(r'\1', BRIGHT_CYAN + BOLD), text)
        text = text.replace('(recommended)', self._colorize('(recommended)', GREEN + BOLD))
        
        return super()._format_text(text)
