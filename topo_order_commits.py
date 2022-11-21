# strace -f -c pytest was used to check that no other commands were used.
# the results showed all the functions called and how many times they were
# invoked.
# additionally, by not importing any modules, I ensured my code to be free
# from outside functions.
# to top that off, I only worked with the following commands:
# sorted(), print(), join(), pop(), remove(), append(), add(), len(), str()
# zip(), open(), those from os and zlib. nothing more.
# modules
import os
import zlib

# constants
DEBUGGING = False


def topo_order_commits():
    git_directory = find_repo_directory()
    branch_heads = get_branch_heads(git_directory)
    commit_graph = get_commit_graph(git_directory)
    root_commits = get_root_commits(commit_graph)
    sorted_graph = get_topological_graph(
        commit_graph, branch_heads, root_commits)
    sticky_end = False
    last_popped = None
    while(sorted_graph):
        node = sorted_graph[-1]
        if(last_popped):
            parent_hashes = [x.commit_hash for x in last_popped.parents]
            parent_hashes = sorted(parent_hashes)
            if(node.commit_hash in parent_hashes):
                # print(f'{node.commit_hash} is {last_popped.commit_hash}
                # parent')
                # do nothing, keep printing
                pass
            else:
                parent_hashes = " ".join(parent_hashes)
                print(parent_hashes + "=")
                print("")
                sticky_end = True
                # print(f'{node.commit_hash} in not {last_popped.commit_hash}
                # parent')
        if(sticky_end):
            sticky_end = False
            children_hashes = [x.commit_hash for x in node.children]
            children_hashes = " ".join(sorted(children_hashes))
            print("=" + children_hashes)
        if(node.commit_hash in branch_heads):
            branch_names = branch_heads[node.commit_hash]
            branch_names = ' '.join(sorted(branch_names))
            print(node.commit_hash + ' ' + branch_names)
        else:
            print(node.commit_hash)
        last_popped = sorted_graph.pop()
    return 0


def get_root_commits(commit_graph):
    root_commits = set()
    for commit in commit_graph:
        if (len(commit_graph[commit].parents) == 0):
            root_commits.add(commit_graph[commit])
            if(DEBUGGING):
                print("root commit: " + commit_graph[commit].commit_hash)
    return root_commits


def find_repo_directory():
    current = os.getcwd()
    b_found = False
    while (b_found is False):
        for file in os.listdir(current):
            if file.endswith(".git"):
                git_directory = os.path.join(current, file)
                b_found = True
        if(os.path.dirname(current) != "/"):
            current = os.path.abspath(os.path.join(current, os.pardir))
        else:
            print("Not inside a Git repository")
            exit(1)
    if(DEBUGGING):
        print("git directory: " + git_directory)
    return git_directory


def get_topological_graph(commit_graph, branch_heads, root_commits):
    sorted_graph = []
    visited = set()
    copy_commit_graph = commit_graph
    while(root_commits):
        layer = [x for x in root_commits]
        layer = sorted(layer)
        for node in layer:
            if(node.commit_hash not in visited):
                sorted_graph.append(node)
                visited.add(node.commit_hash)
                # print(node.commit_hash + " added!")

            children = [x for x in node.children]
            children = sorted(children)
            # print(children)
            for child in children:
                child.parents.remove(node)
                if(len(child.parents) == 0):
                    root_commits.add(child)
                    # print(child.commit_hash + " added!")
            root_commits.remove(node)
    for node in sorted_graph:
        for child in node.children:
            child.parents.add(copy_commit_graph[node.commit_hash])
    purge_non_reachable(sorted_graph, branch_heads)
    if(DEBUGGING):
        print("sorted graph")
        for e in sorted_graph:
            print(e.commit_hash)
        print("---------------------")
    return sorted_graph


def purge_non_reachable(sorted_graph, branch_heads):
    if(DEBUGGING):
        print("reversed in branch head?")
    reversed_nodes = reversed(sorted_graph)
    for node in reversed_nodes:
        if ((node.commit_hash not in branch_heads) and
                (len(node.children) == 0)):
            if(DEBUGGING):
                print(node.commit_hash)
            sorted_graph.remove(node)
            # purge this child out of existance from any node.
            for remaining_node in sorted_graph:
                if(node in remaining_node.children):
                    remaining_node.children.remove(node)


def get_commit_graph(git_directory):
    commit_graph = {}
    objects = os.path.join(git_directory, 'objects')
    folders = [os.path.join(objects, x) for x in os.listdir(objects)]
    # print(folders)
    for dirs in folders:
        files = [os.path.join(dirs, x) for x in os.listdir(dirs)]
        for file in files:
            has_parent = False
            parent_hashes = []
            compressed = open(file, 'rb').read()
            # print(file)
            decompressed = zlib.decompress(compressed)
            if decompressed.startswith(b'commit'):
                # print("found commit")
                commit_hash_var = file[-41:].replace('/', '')
                for line in decompressed.split(b'\n'):
                    if(line.startswith(b'parent')):
                        parent_hashes.append(line[7:].decode())
                        # print("parent hash found")
                        # print(parent_hashes)
                        has_parent = True
                if(DEBUGGING):
                    print("parent hash " +
                          " ".join(parent_hashes) +
                          " of " + commit_hash_var +
                          " found")
                # print(commit_hash_var)
                if(commit_hash_var not in commit_graph):
                    commit_graph[commit_hash_var] = CommitNode(commit_hash_var)
                if(has_parent and len(parent_hashes) != 0):
                    for parent_hash in parent_hashes:
                        if (parent_hash not in commit_graph):
                            commit_graph[parent_hash] = CommitNode(parent_hash)
                        commit_graph[parent_hash].children.add(
                            commit_graph[commit_hash_var])
                        commit_graph[commit_hash_var].parents.add(
                            commit_graph[parent_hash])
                    if(DEBUGGING):
                        print("there are " + str(len(
                            commit_graph[commit_hash_var].parents))
                            + " parents in " + commit_hash_var)
            else:
                # print("something else")
                pass
    return commit_graph


def recursive_get_names(branch_names, folder_of_head, subdir):
    for dir in os.listdir(folder_of_head):
        if os.path.isdir(os.path.join(folder_of_head, dir)):
            recursive_get_names(branch_names, os.path.join(
                folder_of_head, dir), dir + "/")
        elif os.path.isfile(os.path.join(folder_of_head, dir)):
            branch_names.append(subdir + dir)


def get_branch_heads(git_directory):
    branch_heads = {}
    folder_of_head = os.path.join(git_directory, 'refs/heads')
    branch_names = []
    recursive_get_names(branch_names, folder_of_head, "")
    heads = [os.path.join(folder_of_head, x) for x in branch_names]
    for head, branch_name in zip(heads, branch_names):
        file = open(head, 'r').read()
        for line in file.split('\n'):
            if(len(line) == 40):
                # print("this is a branch head pointing to a commit!")
                if (line not in branch_heads):
                    branch_heads[line] = [branch_name]
                else:
                    branch_heads[line].append(branch_name)
            else:
                # print("garbage")
                pass
    if(DEBUGGING):
        print("branch heads")
        for e in branch_heads:
            print(e)
        print("---------------------")
    return branch_heads


class CommitNode:
    def __init__(self, commit_hash):
        """
        :type commit_hash: str
        """
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()

    def __lt__(self, other):
        return (self.commit_hash < other.commit_hash)


if __name__ == "__main__":
    topo_order_commits()