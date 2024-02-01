#
#    Copyright 2024 konawasabi
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

'''
'''

import os
import sys
import pathlib
import re
import argparse

from lark import Lark, Transformer, v_args, Visitor

from kobushi import loadmapgrammer as lgr
from kobushi import loadheader as lhe

from kobushi import mapinterpreter

@v_args(inline=True)
class MapInterpreter(mapinterpreter.ParseMap):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def map_element(self, *argument): # map_elementの引数をリストに変換して返す
        a = 1
        #print('@',argument)
        result = []
        for i in argument:
            if(i.data == 'mapobject'):
                label = i.children[0]
                key = i.children[1]
                #print('mapobject: label=',label,', key=',key)
                if label == 'Track':
                    result.append(label.value)
                    result.append(key)
                else:
                    result.append(label.value)
            elif(i.data == 'mapfunc'):
                label = i.children[0]
                f_arg = i.children[1:]
                #print('mapfunc: label=',label,', args=',f_arg)
                result.append(label.value)
                result.append(f_arg)
        #print()
        return result if 'Track' in result else None
    def include_file(self, path): # include構文はreadfileで処理するので、インタプリターでは無視する
        pass

def readfile(filename, input_root, result_list, tr_params, trackkey, include_file=None):#offset_label, offset_val, result_list, input_root, inverse_kp = False):
    '''マップファイルを読み込み、Track構文の引数を書き換える
    
    Parameters:
    -----
    filename : str
      読み込むファイルへのパス
    input_root : pathlib.Path
      読み込むファイルの親ディレクトリへのパス
    result_list : list
      結果を格納するリスト。
    tr_params : dict
      Track.Position構文の引数を変換する係数
    trackkey : str
      変換対象となる軌道キー。''の場合は全ての軌道を処理する。
    include_file : str
      マップファイル内include要素の引数を指定する
    -----

    result_listのフォーマット
      [{'filename':str, 'data':str}, ...]
    
    '''

    mapinterp = MapInterpreter(None,None,prompt=True)
        
    path, rootpath, header_enc = lhe.loadheader(filename, 'BveTs Map ',2)
    fp = open(path,'r',encoding=header_enc)
    fp.readline()
    fbuff = fp.read()
    fp.close()

    output = 'BveTs Map 2.02\n'

    grammer = lgr.loadmapgrammer()
    parser = Lark(grammer, parser='lalr')

    rem_comm = re.split('#.*\n',fbuff)
    comm = re.findall('#.*\n',fbuff)

    ix_comm = 0
    for item in rem_comm:
        statements = item.split(';')
        for elem in statements:
            pre_elem = re.match('^\s*',elem).group(0)                
            elem = re.sub('^\s*','',elem)
            result = mapinterp.transform(mapinterp.parser.parse(elem+';'))
            if len(elem)>0:
                tree = parser.parse(elem+';')
                if tree.data == 'include_file':
                    print('include')
                    readfile(input_root.joinpath(re.sub('\'','',tree.children[0].children[0])),\
                             input_root, result_list, tr_params, trackkey, \
                             include_file=re.sub('\'','',tree.children[0].children[0]))
                    output += pre_elem + elem + ';'
                elif tree.data == 'map_element':
                    label = tree.children[0].children[0]
                    key = tree.children[0].children[1].children[0].value
                    if label == 'Track' and (result[1].lower() == trackkey.lower() or trackkey == ''):
                        
                        #print(result)
                        outstr = ''
                        if result[2].lower() == 'x':
                            outstr = 'Track[\'{:s}\'].X.Interpolate('.format(result[1]+'_mod')
                            if len(result[4]) == 1 and result[4][0] == None:
                                outstr +=')'
                            elif len(result[4]) == 1:
                                outstr += '{:f})'.format(result[4][0]*tr_params['x']['mul']+tr_params['x']['offs'])
                            else:
                                outstr += '{:f},{:f})'.format(result[4][0]*tr_params['x']['mul']+tr_params['x']['offs'],\
                                                              result[4][1]*tr_params['rx']['mul']+tr_params['rx']['offs'])
                            #print('@: '+outstr)
                        elif result[2].lower() == 'y':
                            outstr = 'Track[\'{:s}\'].y.Interpolate('.format(result[1]+'_mod')
                            if len(result[4]) == 1 and result[4][0] == None:
                                outstr +=')'
                            elif len(result[4]) == 1:
                                outstr += '{:f})'.format(result[4][0]*tr_params['y']['mul']+tr_params['y']['offs'])
                            else:
                                outstr += '{:f},{:f})'.format(result[4][0]*tr_params['y']['mul']+tr_params['y']['offs'],\
                                                              result[4][1]*tr_params['ry']['mul']+tr_params['ry']['offs'])
                            #print('@: '+outstr)
                        elif result[2].lower() == 'position':
                            outstr = 'Track[\'{:s}\'].Position('.format(result[1]+'_mod')
                            if len(result[3]) == 2:
                                outstr += '{:f},{:f})'.format(result[3][0]*tr_params['x']['mul']+tr_params['x']['offs'],\
                                                              result[3][1]*tr_params['y']['mul']+tr_params['y']['offs'])
                            elif len(result[3]) == 3:
                                outstr += '{:f},{:f},{:f})'.format(result[3][0]*tr_params['x']['mul']+tr_params['x']['offs'],\
                                                                   result[3][1]*tr_params['y']['mul']+tr_params['y']['offs'],\
                                                                   result[3][2]*tr_params['rx']['mul']+tr_params['rx']['offs'])
                            elif len(result[3]) == 4:
                                outstr += '{:f},{:f},{:f},{:f})'.format(result[3][0]*tr_params['x']['mul']+tr_params['x']['offs'],\
                                                                   result[3][1]*tr_params['y']['mul']+tr_params['y']['offs'],\
                                                                        result[3][2]*tr_params['rx']['mul']+tr_params['rx']['offs'],\
                                                                   result[3][3]*tr_params['ry']['mul']+tr_params['ry']['offs'])
                            #print('@: '+outstr)
                        else:
                            outstr = elem
                        output += pre_elem + outstr + ';'
                    else:
                        output += pre_elem + elem + ';'
                else:
                    output += pre_elem + elem + ';'
            else:
                output += pre_elem
        
        if ix_comm < len(comm):
            output += comm[ix_comm]
            ix_comm+=1
            
    result_list.append({'filename':filename, 'include_file':include_file, 'data':output})

def writefile(result, output_root):
    ''' readfileで生成したresult_listをファイルに出力する

    Parameters:
    -----
    result : list
      readfileが出力するresult_list
    output_root : pathlib.Path
      データを出力するディレクトリへのパス
    '''
    for data in result:
        if data['include_file'] is None:
            os.makedirs(output_root,exist_ok=True)
            fp = open(output_root.joinpath(pathlib.Path(data['filename']).name),'w')
        else:
            os.makedirs(output_root.joinpath(pathlib.Path(data['include_file']).parent),exist_ok=True)
            fp = open(output_root.joinpath(data['include_file']),'w')
        fp.write(data['data'])
        fp.close()

        if False:
            print(data['filename'])
            print(data['data'])

def procpath(pathstr):
    ''' readfileへ渡すPathオブジェクトを生成する
    '''
    input_path = pathlib.Path(pathstr)
    inroot = input_path.parent
    return input_path, inroot

if __name__ == '__main__':
    
    if False:
        import pdb
        pdb.set_trace()
    argp = argparse.ArgumentParser()
    argp.add_argument('filepath', metavar='FILE', type=str, help='input map file', nargs='?')
    argp.add_argument('coeffs', metavar='N', type=float, nargs='*', help='ax, bx, ay, by, arx, brx, ary, bry')
    argp.add_argument('-o', '--outputdir', help='output directory', type=str)
    argp.add_argument('-k', '--trackkey', help='target trackkey', type=str, default='')
    args = argp.parse_args()
    
    input_path, inroot = procpath(args.filepath)
    if args.outputdir is None:
        outroot = inroot.joinpath('result')
    else:
        outroot = pathlib.Path(args.outputdir)

    tr_params = {'x' :{'mul':1.0,'offs':0},\
                 'y' :{'mul':1.0,'offs':0},\
                 'rx':{'mul':1.0,'offs':0},\
                 'ry':{'mul':1.0,'offs':0}}

    #print(args)

    tr_params_index = [['x','x','y','y','rx','rx','ry','ry'],['mul','offs','mul','offs','mul','offs','mul','offs']]

    for i in range(len(args.coeffs)):
        tr_params[tr_params_index[0][i]][tr_params_index[1][i]]=args.coeffs[i]

    #print(tr_params)

    result = []
    readfile(str(input_path), inroot, result, tr_params, args.trackkey)
    writefile(result, outroot)
